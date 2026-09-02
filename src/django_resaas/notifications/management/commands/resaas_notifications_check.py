import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from django_resaas.notifications.enums import OutboxStatus


def _provider_status(env_vars):
    """True/False only - never the actual values (spec: never print secrets)."""
    return all(os.environ.get(var) for var in env_vars)


class Command(BaseCommand):
    help = "Health check for the notifications system: what's configured, what's stuck, whether the queue is reachable. Never prints secrets."

    def handle(self, *args, **options):
        from django_resaas.notifications.models import NotificationOutbox

        enabled = getattr(settings, "NOTIFICATIONS_ENABLED", False)
        self.stdout.write(
            f"Notifications system: {'enabled' if enabled else 'disabled'}"
        )

        email_ok = bool(
            getattr(settings, "EMAIL_HOST", None)
            or getattr(settings, "EMAIL_BACKEND", None)
        )
        sms_ok = _provider_status(
            ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"]
        )
        whatsapp_ok = _provider_status(
            ["WHATSAPP_CLOUD_API_TOKEN", "WHATSAPP_CLOUD_API_PHONE_NUMBER_ID"]
        )

        self.stdout.write(f"Email provider: {'configured' if email_ok else 'missing'}")
        self.stdout.write(f"SMS provider: {'configured' if sms_ok else 'missing'}")
        self.stdout.write(
            f"WhatsApp provider: {'configured' if whatsapp_ok else 'missing'}"
        )

        self.stdout.write("")

        counts = {
            status: NotificationOutbox.objects.filter(status=status).count()
            for status in [
                OutboxStatus.PENDING,
                OutboxStatus.RETRY,
                OutboxStatus.FAILED,
                OutboxStatus.DISPATCHING,
                OutboxStatus.PROCESSING,
            ]
        }

        self.stdout.write(f"Outbox pending: {counts[OutboxStatus.PENDING]}")
        self.stdout.write(f"Retry: {counts[OutboxStatus.RETRY]}")
        self.stdout.write(f"Failed: {counts[OutboxStatus.FAILED]}")

        dispatch_timeout = getattr(settings, "OUTBOX_DISPATCH_TIMEOUT", 300)
        processing_timeout = getattr(settings, "OUTBOX_PROCESSING_TIMEOUT", 300)
        now = timezone.now()

        stuck = NotificationOutbox.objects.filter(
            status=OutboxStatus.DISPATCHING,
            dispatching_at__lte=now - timezone.timedelta(seconds=dispatch_timeout),
        ).count()
        stuck += NotificationOutbox.objects.filter(
            status=OutboxStatus.PROCESSING,
            processing_at__lte=now - timezone.timedelta(seconds=processing_timeout),
        ).count()

        self.stdout.write(f"Stuck: {stuck}")

        oldest_pending = (
            NotificationOutbox.objects.filter(
                status__in=[OutboxStatus.PENDING, OutboxStatus.RETRY]
            )
            .order_by("scheduled_at")
            .values_list("scheduled_at", flat=True)
            .first()
        )
        self.stdout.write(f"Oldest pending: {oldest_pending or '-'}")

        self.stdout.write("")

        broker_url = getattr(settings, "CELERY_BROKER_URL", None)
        if not broker_url:
            self.stdout.write("Queue: not configured (CELERY_BROKER_URL unset)")
        else:
            self.stdout.write(f"Queue: {self._check_broker()}")

        self.stdout.write(
            "Recovery configuration: "
            f"batch_size={getattr(settings, 'NOTIFICATION_OUTBOX_BATCH_SIZE', 100)}, "
            f"interval={getattr(settings, 'OUTBOX_RECOVERY_INTERVAL_SECONDS', 30)}s, "
            f"max_attempts={getattr(settings, 'OUTBOX_MAX_ATTEMPTS', 5)}, "
            f"retry_base={getattr(settings, 'OUTBOX_RETRY_BASE_SECONDS', 30)}s, "
            f"retry_max={getattr(settings, 'OUTBOX_RETRY_MAX_SECONDS', 3600)}s"
        )

    @staticmethod
    def _check_broker():
        try:
            from django_resaas.notifications.tasks import process_notification

            connection = process_notification.app.connection()
            connection.ensure_connection(max_retries=1, timeout=2)
            connection.close()
            return "reachable"
        except Exception as exc:
            return f"unreachable ({exc.__class__.__name__})"
