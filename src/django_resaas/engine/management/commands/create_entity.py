from django.core.management.base import BaseCommand
from django_resaas.engine.core.services.user_service import UserService
from django_resaas.engine.core.services.bootstrap_service import BootstrapService






class Command(BaseCommand):
    help = "Bootstrap inicial do SaaS"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Bootstrap SaaS \n\n"))

        entity_type = input("Enter your Entity Type name.: ")
        entity = input("Enter your Entity name.: ")
        branch = input("Enter your branch name: ")
        group = "Admin"

        user = UserService.get_or_create_superuser(self.stdout, style=self.style)
 
        result = BootstrapService.run(entity_type, entity, branch, user, group, stdout=self.stdout, style=self.style)

        self.stdout.write(
            self.style.SUCCESS(f"✔ Superuser created:\t{user.email} \n")
        )
        self.stdout.write(
            self.style.NOTICE(f"👤 Username:\t{user.username} \n")
        )
       
        self.stdout.write(self.style.SUCCESS("\n 🛠 ⚙️ Ready-to-use system\n"))
