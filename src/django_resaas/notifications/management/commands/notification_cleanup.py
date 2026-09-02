from django.core.management.base import BaseCommand

from django_resaas.notifications.tasks import cleanup_notifications


class Command(BaseCommand):
    help = "Delete sent/failed/cancelled NotificationOutbox/DeliveryAttempt rows past their retention window (NOTIFICATION_OUTBOX_RETENTION_DAYS / NOTIFICATION_ATTEMPT_RETENTION_DAYS)."

    def handle(self, *args, **options):
        result = cleanup_notifications()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {result['deleted_outboxes']} outbox row(s), "
                f"{result['deleted_attempts']} delivery attempt(s)."
            )
        )
