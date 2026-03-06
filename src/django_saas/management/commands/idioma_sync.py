from django.core.management.base import BaseCommand
from django_saas.core.services.traducao_sinc_service import TraducaoSyncService





class Command(BaseCommand):
    help = "Bootstrap inicial do SaaS"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Sync Traducao SaaS \n\n"))

        TraducaoSyncService.sync( stdout=self.stdout, style=self.style )

        self.stdout.write(self.style.SUCCESS("\n 🛠 ⚙️ Idiomas Sincronizadas, pronto para uso\n"))
