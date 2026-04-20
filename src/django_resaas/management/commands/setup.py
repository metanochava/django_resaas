from django.core.management.base import BaseCommand
from django_resaas.core.services.idioma_service import IdiomaService
from django_resaas.core.services.frontend_service import FrontEndService
from django_resaas.core.services.traducao_service import TraducaoService

class Command(BaseCommand):
    help = "Bootstrap inicial do SaaS"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Bootstrap SaaS \n\n"))

        IdiomaService.load_defaults( stdout=self.stdout, style=self.style )

        FrontEndService.load_defaults( stdout=self.stdout,  style=self.style  )

        TraducaoService.load_defaults( stdout=self.stdout, style=self.style )

        self.stdout.write(self.style.SUCCESS("\n 🛠 ⚙️ Sistema pronto para uso\n"))
