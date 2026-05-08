from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from getpass import getpass
from django_resaas.models.entity_type import EntityType
from django_resaas.models.entity import Entity
from django_resaas.models.branch import Branch
from django_resaas.models.entity_user import EntityUser
from django_resaas.models.branch_user import BranchUser
from django_resaas.models.branch_user_group import BranchUserGroup
from django.contrib.auth.models import Group
from django_resaas.core.services.frontend_service import FrontEndService
from django_resaas.core.services.language_service import LanguageService
from django_resaas.models.app import App
from django_resaas.models.entity_type_app import EntityTypeApp
from django_resaas.models.entity_app import EntityApp

from django_resaas.models.entity_type_group import EntityTypeGroup
from django_resaas.models.entity_group import EntityGroup
from django_resaas.models.branch_group import BranchGroup

User = get_user_model()

GROUPS_WITH_ID = [
"Guest",
"Admin",
"Root",
]




class Command(BaseCommand):
    help = """
    Enterprise Bootstrap Command

    This command initializes the entire SaaS environment by creating a fully configured superuser
    and setting up the complete system structure required for operation.

    Features:

    ✔ Interactive creation of a superuser (username, email, password)
    ✔ Email uniqueness validation
    ✔ Secure password input (hidden typing)
    ✔ Automatic email verification flag
    ✔ Creation of core SaaS structure:
        - Entity Type (multi-tenant template)
        - Entity (tenant instance)
        - Branch (operational unit)

    ✔ Automatic assignment of relationships:
        - User → Entity (as admin)
        - User → Branch

    ✔ Group management:
        - Creates default groups (e.g., Guest, Admin, Root)
        - Assigns groups to:
            • Entity Type
            • Entity
            • Branch
            • User

    ✔ Application bootstrap:
        - Registers core applications
        - Links applications to Entity Type and Entity

    ✔ Loads system defaults:
        - Frontend configuration
        - Language settings

    Security & Validation:

    ⚠ Prevents duplicate email registration
    ⚠ Enforces password confirmation
    ⚠ Ensures consistent system initialization

    Usage:

        python manage.py <command_name>

    Example:

        python manage.py bootstrap

    Expected Output:

        ✔ Superuser successfully created
        ✔ SaaS environment initialized
        ✔ Groups and permissions assigned
        ✔ Applications registered
        ✔ System ready for use

    Notes:

    - This command is intended for initial system setup.
    - Should be executed once per environment.
    - Credentials generated should be stored securely.

    """

    def handle(self, *args, **options):
        email = "root@co.mz"
        username = "root"

        while True:
            username = input("Write username: ")
            email = input("Write a valid e-mail: ")
            user = User.objects.filter(email=email).first()
            if user :
                self.stdout.write(
                    self.style.WARNING("\nThe e-mail is already exist.")
                )
                continue

            break



        # 🔐 pedir password pelo teclado (sem mostrar)
        while True:
            password = getpass("Superuser password: ")
            password_confirm = getpass("Confirm password: ")

            if not password:
                self.stdout.write(
                    self.style.ERROR("The password cannot be empty.")
                )
                continue

            if password != password_confirm:
                self.stdout.write(
                    self.style.ERROR("As passwords não coincidem")
                )
                continue

            break
        if not exist:
            user = User.objects.create_superuser(
                email=email,
                username=username,
                password=password,
            )

            user.set_password(password)
            user.is_verified_email= True
            user.save()


        data = {
            "entity_type": "SaaS",
            "entity": "Entity",
            "branch": "Main",
        }

        # ------------------------
        # 1. EntityType
        # ------------------------
        entity_type, _ = EntityType.objects.get_or_create(
            name=data["entity_type"],
            estado = 1
        )

        # ------------------------
        # 2. Entity
        # ------------------------
        entity, created_entity = Entity.objects.get_or_create(
            name=data["entity"],
            entity_type=entity_type,
            estado = 1
        )

        # ManyToMany → DEPOIS
        entity.admins.add(user)

        EntityUser.objects.get_or_create(
            user=user,
            entity=entity,
            estado = 1
        )

        # ------------------------
        # 3. Branch
        # ------------------------
        branch, _ = Branch.objects.get_or_create(
            name=data["branch"],
            entity=entity,
            estado = 1
        )

        BranchUser.objects.get_or_create(
            user=user,
            branch=branch,
            estado = 1
        )

        # ------------------------
        # 4. Group
        # ------------------------
        for gname in GROUPS_WITH_ID:

            group, _ = Group.objects.get_or_create(
                name = gname
            )


            BranchUserGroup.objects.get_or_create(
                user=user,
                branch=branch,
                group=group,
                estado = 1
            )

            user.groups.add(group)

            EntityTypeGroup.objects.get_or_create(
                entity_type=entity_type,
                group=group,
                estado = 1
            )

            EntityGroup.objects.get_or_create(
                entity=entity,
                group=group,
                estado = 1
            )

            BranchGroup.objects.get_or_create(
                branch=branch,
                group=group,
                estado = 1
            )

        self.stdout.write(self.style.WARNING(f"\n"))

        for name in ['django_resaas',]:
            app, _ = App.objects.get_or_create(
                name=name,
                estado = 1
            )

            entity_type_app, _ = EntityTypeApp.objects.get_or_create(
                app=app,
                entity_type=entity_type,
                estado = 1
            )

            entity_app, _ = EntityApp.objects.get_or_create(
                app=app,
                entity=entity,
                estado = 1
            )

            self.stdout.write(self.style.WARNING(f"✔ {'App:':20} {app.name}"))

        FrontEndService.load_defaults( stdout=self.stdout,  style=self.style  )
        LanguageService.load_defaults( stdout=self.stdout, style=self.style )

        self.stdout.write(self.style.HTTP_INFO(f""))
        self.stdout.write(self.style.HTTP_INFO(f""))
        self.stdout.write(self.style.HTTP_INFO(f"{'':10} {'✔ Superuser created:'}"))
        self.stdout.write(self.style.HTTP_INFO(f""))
        self.stdout.write(self.style.HTTP_INFO(f"{'Email:':20} {user.email}"))
        self.stdout.write(self.style.SUCCESS(f"{'User:':20} {user.username}"))
        self.stdout.write(self.style.HTTP_SUCCESS(f"{'EntityType:':20} {entity_type.name}"))
        self.stdout.write(self.style.HTTP_NOT_MODIFIED(f"{'Entity:':20} {entity.name}"))
        self.stdout.write(self.style.HTTP_SERVER_ERROR(f"{'Branch:':20} {branch.name}"))
        self.stdout.write(self.style.WARNING(f"{'Groups:':20} Guest, Admin, Root"))
        self.stdout.write(self.style.ERROR("⚠️ Keep these credentials safe."))
        self.stdout.write(self.style.HTTP_INFO(f""))
        self.stdout.write(self.style.HTTP_INFO(f""))


