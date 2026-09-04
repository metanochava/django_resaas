from django.core.management.base import BaseCommand

from django_resaas.engine.management.commands.resaas_setup import run_setup


class Command(BaseCommand):
    help = "Bootstrap inicial do SaaS (legacy alias - see `resaas_setup`)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Bootstrap SaaS \n\n"))
        run_setup(self.stdout, self.style)
        self.stdout.write(self.style.SUCCESS("\n 🛠 ⚙️ Sistema pronto para uso\n"))
