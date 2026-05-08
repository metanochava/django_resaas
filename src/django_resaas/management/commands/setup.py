from django.core.management.base import BaseCommand
from django_resaas.core.services.language_service import LanguageService
from django_resaas.core.services.frontend_service import FrontEndService
from django_resaas.core.services.translation_service import TranslationService

class Command(BaseCommand):
    help = "Bootstrap inicial do SaaS"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Bootstrap SaaS \n\n"))

        LanguageService.load_defaults( stdout=self.stdout, style=self.style )

        FrontEndService.load_defaults( stdout=self.stdout,  style=self.style  )

        TranslationService.load_defaults( stdout=self.stdout, style=self.style )

        self.stdout.write(self.style.SUCCESS("\n 🛠 ⚙️ Sistema pronto para uso\n"))
