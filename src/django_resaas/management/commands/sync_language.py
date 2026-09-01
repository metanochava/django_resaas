from django.core.management.base import BaseCommand
from django_resaas.core.services.translation_sync_service import TranslationSyncService





class Command(BaseCommand):
    help = "Bootstrap inicial do SaaS"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Sync Translation SaaS \n\n"))

        TranslationSyncService.sync( stdout=self.stdout, style=self.style )

        self.stdout.write(self.style.SUCCESS("\n 🛠 ⚙️ Languages Sincronizadas, pronto para uso\n"))
