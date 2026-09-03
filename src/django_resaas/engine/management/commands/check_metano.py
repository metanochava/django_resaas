import pathlib
import sys
from django.core.management.base import BaseCommand, CommandError

FORBIDDEN = [
    "models.Model",
    "ModelSerializer",
    "ModelViewSet",
    "from .",
]


class Command(BaseCommand):
    help = "Checks whether the project follows the MetanoStack standard"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default=".",
            help="Project path (default: .)"
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail the command if errors are found"
        )

    def handle(self, *args, **options):
        path = options["path"]
        strict = options["strict"]

        errors = self.check_project(path)

        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(e))

            if strict:
                raise CommandError("MetanoStack compliance FAILED")

            return

        self.stdout.write(self.style.SUCCESS("MetanoStack compliance OK"))

    def check_project(self, path="."):
        errors = []
        for py in pathlib.Path(path).rglob("*.py"):
            try:
                text = py.read_text()
            except Exception:
                continue

            for rule in FORBIDDEN:
                if rule in text:
                    errors.append(f"{py}: Forbidden pattern -> {rule}")
        return errors
