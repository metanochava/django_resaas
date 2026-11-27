from django.core.management.base import BaseCommand, CommandError

from django_resaas.saas.core.services.menu_validator import MenuValidator


class Command(BaseCommand):
    help = (
        "Validate the database menus: missing models, resources, routes, "
        "permissions, parents, cycles and inactive modules. Read only. "
        "Exits with an error when any problem has severity 'error'."
    )

    def handle(self, *args, **options):
        issues = MenuValidator.validate()

        if not issues:
            self.stdout.write(self.style.SUCCESS("Menus: no problems found."))
            return

        for issue in issues:
            location = " ".join(
                part for part in (
                    f"menu={issue.menu_code}" if issue.menu_code else "",
                    f"item={issue.item_id}" if issue.item_id else "",
                ) if part
            )
            line = f"[{issue.severity}] {issue.code}: {issue.message} ({location})"
            if issue.severity == "error":
                self.stderr.write(self.style.ERROR(line))
            else:
                self.stdout.write(self.style.WARNING(line))

        errors = sum(1 for issue in issues if issue.severity == "error")
        if errors:
            raise CommandError(f"{errors} menu error(s) found.")
