from django.core.management.base import BaseCommand
from django.db import transaction

from django_resaas.saas.core.services.group_access_service import editable_eligibility
from django_resaas.saas.models.group import Group


class Command(BaseCommand):

    help = (
        "Marks as editable the existing groups that belong to ONE entity only "
        "(Group.editable). Only editable groups can have their permissions "
        "changed by that entity's own admins; shared, template and platform "
        "groups stay platform-level (see core/services/group_access_service.py). "
        "Dry run by default - pass --apply to write. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the changes (default: only report what would change).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        to_mark, skipped = [], []

        for group in Group.objects.order_by("name"):
            eligible, reason = editable_eligibility(group)
            (to_mark if eligible else skipped).append((group, reason))

        for group, reason in skipped:
            self.stdout.write(f"  skip  {group.name}: {reason}")
        for group, reason in to_mark:
            self.stdout.write(self.style.SUCCESS(f"  mark  {group.name}: {reason}"))

        if not apply:
            self.stdout.write(self.style.WARNING(
                f"Dry run: {len(to_mark)} group(s) would be marked editable, "
                f"{len(skipped)} left unchanged. Run again with --apply to write."
            ))
            return

        with transaction.atomic():
            updated = Group.objects.filter(
                id__in=[group.id for group, _ in to_mark], editable=False
            ).update(editable=True)

        self.stdout.write(self.style.SUCCESS(
            f"Marked {updated} group(s) editable; {len(skipped)} left unchanged."
        ))
