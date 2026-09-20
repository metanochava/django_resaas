from django.core.management.base import BaseCommand

from django_resaas.saas.core.services import temporary_password_service


class Command(BaseCommand):
    help = (
        "Retire every OVERDUE temporary password: its recoverable (encrypted) "
        "copy is destroyed and TEMPORARY_PASSWORD_EXPIRED audited. Idempotent - "
        "run it from cron/a scheduler; expiry is also enforced lazily at login "
        "and when a password is viewed."
    )

    def handle(self, *args, **options):
        count = temporary_password_service.expire_overdue()

        self.stdout.write(f"{count} temporary password(s) expired.")
