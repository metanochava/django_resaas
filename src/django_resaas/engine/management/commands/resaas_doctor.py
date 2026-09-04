import json

from django.core.management.base import BaseCommand, CommandError

from django_resaas.engine.core.doctor import checks  # noqa: F401  (populates CHECK_REGISTRY)
from django_resaas.engine.core.doctor.base import CHECK_REGISTRY, CheckResult

LEVEL_ORDER = {"info": 0, "success": 1, "warning": 2, "error": 3}
LEVEL_TAG = {"info": "INFO", "success": "OK", "warning": "WARNING", "error": "ERROR"}


class Command(BaseCommand):

    help = (
        "Structural diagnostic for a RESAAS installation: database, "
        "migrations, registered views, actions, schema, permissions and "
        "module metadata. Read-only - observes, never writes to the "
        "database. Safe to run in production and CI/CD."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Emit machine-readable JSON only (no human-formatted output mixed in).",
        )
        parser.add_argument(
            "--check",
            action="append",
            dest="only_checks",
            metavar="NAME",
            help="Run only this check (repeatable). Default: all registered checks.",
        )
        parser.add_argument(
            "--fail-on-warning",
            action="store_true",
            help="Exit with code 1 if only warnings were found (errors always exit 2).",
        )

    def handle(self, *args, **options):
        as_json = options["as_json"]
        only = options.get("only_checks")
        fail_on_warning = options["fail_on_warning"]

        names = only or sorted(CHECK_REGISTRY)
        unknown = [name for name in names if name not in CHECK_REGISTRY]

        if unknown:
            raise CommandError(
                f"Unknown check(s): {', '.join(unknown)}. "
                f"Available: {', '.join(sorted(CHECK_REGISTRY))}"
            )

        report = []
        for name in names:
            check = CHECK_REGISTRY[name]
            try:
                results = check.run()
            except Exception as exc:
                results = [
                    CheckResult(
                        f"{name}.crashed",
                        "error",
                        f"Check '{name}' raised {exc.__class__.__name__}: {exc}",
                        {},
                    )
                ]
            report.append((check, results))

        errors = sum(1 for _, results in report for r in results if r.level == "error")
        warnings = sum(1 for _, results in report for r in results if r.level == "warning")
        status = "failed" if errors else ("warning" if warnings else "ok")

        if as_json:
            self._print_json(report, status, errors, warnings)
        else:
            self._print_human(report, status, errors, warnings)

        if errors:
            raise SystemExit(2)
        if warnings and fail_on_warning:
            raise SystemExit(1)

    # =========================================================
    # OUTPUT
    # =========================================================

    def _print_json(self, report, status, errors, warnings):
        payload = {
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "checks": [
                {
                    "check": check.name,
                    "label": check.label,
                    "results": [r.to_dict() for r in results],
                }
                for check, results in report
            ],
        }
        self.stdout.write(json.dumps(payload))

    def _print_human(self, report, status, errors, warnings):
        self.stdout.write(self.style.MIGRATE_HEADING("RESAAS Doctor"))
        self.stdout.write("-" * 40)
        self.stdout.write("")

        for check, results in report:
            worst_level = max(
                (r.level for r in results),
                key=lambda level: LEVEL_ORDER[level],
                default="success",
            )
            tag = LEVEL_TAG[worst_level]
            self.stdout.write(f"{check.label:<30} {self._style_for(worst_level)(tag)}")

        problems = [
            (r) for _, results in report for r in results if r.level in ("warning", "error")
        ]

        if problems:
            self.stdout.write("")
            self.stdout.write("Problems")
            self.stdout.write("-" * 40)

            for r in problems:
                self.stdout.write("")
                self.stdout.write(
                    self._style_for(r.level)(f"[{LEVEL_TAG[r.level]}] {r.message}")
                )

        self.stdout.write("")
        self.stdout.write("Summary")
        self.stdout.write("-" * 40)
        self.stdout.write(f"Errors      {errors}")
        self.stdout.write(f"Warnings    {warnings}")
        self.stdout.write(f"Status      {status.upper()}")

    def _style_for(self, level):
        return {
            "info": self.style.NOTICE,
            "success": self.style.SUCCESS,
            "warning": self.style.WARNING,
            "error": self.style.ERROR,
        }[level]
