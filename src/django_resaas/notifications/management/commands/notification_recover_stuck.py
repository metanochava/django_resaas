from django.core.management.base import BaseCommand

from django_resaas.notifications.outbox_dispatcher import OutboxDispatcher


class Command(BaseCommand):
    help = "Recover NotificationOutbox rows stuck in dispatching/processing past their timeout."

    def handle(self, *args, **options):
        count = OutboxDispatcher.recover_stuck()
        self.stdout.write(self.style.SUCCESS(f"Recovered {count} stuck outbox row(s)."))
