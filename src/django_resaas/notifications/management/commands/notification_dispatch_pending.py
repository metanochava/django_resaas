from django.core.management.base import BaseCommand

from django_resaas.notifications.outbox_dispatcher import OutboxDispatcher


class Command(BaseCommand):
    help = "Dispatch pending/retry NotificationOutbox rows eligible right now. Thin wrapper around the same service the Celery Beat task calls."

    def handle(self, *args, **options):
        count = OutboxDispatcher.dispatch_eligible_batch()
        self.stdout.write(self.style.SUCCESS(f"Dispatched {count} outbox row(s)."))
