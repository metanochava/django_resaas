import json

from django.core.management.base import BaseCommand

from django_resaas.engine.core.doctor.checks import SchemaCheck


class Command(BaseCommand):

    help = (
        "Validates the RESAAS Schema 1.0 contract (ResaasSchemaBuilder) "
        "for every model behind a registered view. No HTTP, no business "
        "data - only the structural contract the frontend relies on. "
        "Equivalent to `manage.py resaas_doctor --check schema`."
    )

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args, **options):
        results = SchemaCheck().run()
        errors = sum(1 for r in results if r.level == "error")

        if options["as_json"]:
            self.stdout.write(
                json.dumps({"errors": errors, "results": [r.to_dict() for r in results]})
            )
        else:
            self.stdout.write(self.style.MIGRATE_HEADING("RESAAS Schema Check"))
            self.stdout.write("")

            styles = {
                "error": self.style.ERROR,
                "warning": self.style.WARNING,
                "info": self.style.NOTICE,
                "success": self.style.SUCCESS,
            }
            for r in results:
                self.stdout.write(styles[r.level](f"[{r.level.upper()}] {r.message}"))

            self.stdout.write("")
            if errors:
                self.stdout.write(self.style.ERROR(f"{errors} error(s)"))
            else:
                self.stdout.write(self.style.SUCCESS("OK"))

        if errors:
            raise SystemExit(2)
