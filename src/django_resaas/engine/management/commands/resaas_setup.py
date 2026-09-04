from django.core.management.base import BaseCommand

from django_resaas.engine.core.services.frontend_service import FrontEndService
from django_resaas.engine.core.services.language_service import LanguageService
from django_resaas.engine.core.services.translation_service import TranslationService


def run_setup(stdout, style):
    """Prepares the global baseline metadata a RESAAS installation needs to
    work: languages, frontend defaults, translations. Idempotent (every
    service underneath uses get_or_create). Deliberately does NOT create a
    superuser or any tenant structure (Entity/Branch/users) - see
    create_entity/create_root for that - and never touches existing
    business data. Shared by both `setup` (legacy name, kept as a
    compatibility wrapper) and `resaas_setup` (official name) so the two
    commands can never drift apart."""

    LanguageService.load_defaults(stdout=stdout, style=style)
    FrontEndService.load_defaults(stdout=stdout, style=style)
    TranslationService.load_defaults(stdout=stdout, style=style)


class Command(BaseCommand):

    help = (
        "Prepares the global baseline metadata a RESAAS installation "
        "needs: languages, frontend defaults, translations. Safe to run "
        "repeatedly. Does not create a superuser or any tenant - see "
        "create_entity/create_root for that."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("RESAAS Setup\n"))
        run_setup(self.stdout, self.style)
        self.stdout.write(self.style.SUCCESS("\nRESAAS ready.\n"))
