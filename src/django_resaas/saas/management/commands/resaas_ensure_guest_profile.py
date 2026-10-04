"""Gives the Guest profile to every user in every Branch they belong to.

    python manage.py resaas_ensure_guest_profile           # dry run: lists who would get it
    python manage.py resaas_ensure_guest_profile --apply   # assigns it

New memberships get it automatically (core/signals/guest_profile.py); this is
for the users that existed before. Idempotent. Only where the user is already a
member - never in another Entity (core/services/guest_profile_service.py)."""
from django.core.management.base import BaseCommand

from django_resaas.saas.core.services import guest_profile_service as service


class Command(BaseCommand):
    help = "Assign the Guest profile to every user in each Branch they belong to (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Assign it (default: dry run).")

    def handle(self, *args, **options):
        missing = service.memberships_missing_guest()
        if not missing:
            self.stdout.write("Every member already holds Guest in each of their branches: nothing to do.")
            return
        for membership in missing:
            self.stdout.write(f"  {membership.user.username} @ {membership.branch.name} ({membership.branch.entity_id})")
        if not options["apply"]:
            self.stdout.write(self.style.WARNING(f"Dry run: {len(missing)} membership(s) would get Guest. Use --apply."))
            return
        group = service.guest_group()
        changed = sum(1 for m in missing if service.ensure_guest(m.user, m.branch, group))
        self.stdout.write(self.style.SUCCESS(f"Guest assigned in {changed} membership(s)."))
