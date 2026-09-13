import os

from django.core.files import File
from django.core.management.base import BaseCommand
from django_resaas.saas.core.services.user_service import UserService
from django_resaas.saas.core.services.bootstrap_service import BootstrapService
from django_resaas.saas.core.services.bootstrap_email_service import send_bootstrap_welcome_email
from django_resaas.saas.core.utils.image_picker import pick_image_file






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

        if result.get("entity_type_created"):
            tipo = result["entity_type"]
            icon_path = pick_image_file(
                f"Select an icon for the new Entity Type '{tipo.name}'",
                stdout=self.stdout, style=self.style,
            )
            with open(icon_path, "rb") as f:
                tipo.icon.save(os.path.basename(icon_path), File(f), save=True)
            self.stdout.write(self.style.SUCCESS(f"✔ Icon set for Entity Type '{tipo.name}'"))

        if result.get("entity_created"):
            ent = result["entity"]
            logo_path = pick_image_file(
                f"Select a logo for the new Entity '{ent.name}'",
                stdout=self.stdout, style=self.style,
            )
            with open(logo_path, "rb") as f:
                ent.logo.save(os.path.basename(logo_path), File(f), save=True)
            self.stdout.write(self.style.SUCCESS(f"✔ Logo set for Entity '{ent.name}'"))

        self.stdout.write(
            self.style.SUCCESS(f"✔ Superuser created:\t{user.email} \n")
        )
        self.stdout.write(
            self.style.NOTICE(f"👤 Username:\t{user.username} \n")
        )

        email_sent = send_bootstrap_welcome_email(
            user,
            entity=result.get("entity"),
            entity_type=result.get("entity_type"),
            branch=result.get("branch"),
            group=result.get("group"),
        )
        if email_sent:
            self.stdout.write(self.style.SUCCESS(f"✔ Welcome email sent to {user.email}"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Welcome email was not sent (no provider configured or send failed)."))

        self.stdout.write(self.style.SUCCESS("\n 🛠 ⚙️ Ready-to-use system\n"))
