from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from django_resaas.saas.core.services.bootstrap_service import default_modules
from django_resaas.saas.core.services.bootstrap_email_service import (
    send_bootstrap_welcome_email,
)
from django_resaas.saas.core.services.frontend_service import FrontEndService
from django_resaas.saas.core.services.language_service import LanguageService
from django_resaas.saas.core.utils.group_creator import GROUPS
from django_resaas.saas.models.app import App
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.branch_group import BranchGroup
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_app import EntityApp
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity_type_app import EntityTypeApp
from django_resaas.saas.models.entity_type_group import EntityTypeGroup
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.group import Group

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Initializes the SaaS environment, reusing an existing user when "
        "explicitly confirmed."
    )

    def ask_yes_no(self, question, default=False):
        """Ask a yes/no question. Empty input uses the provided default."""
        suffix = "[Y/n]" if default else "[y/N]"
        answer = input(f"{question} {suffix}: ").strip().lower()

        if not answer:
            return default

        return answer in ("y", "yes", "s", "sim")

    def get_or_create_bootstrap_user(self):
        """
        Return (user, created, password).

        Existing users are reused only after explicit confirmation. Their
        password and account fields are not changed by this method.
        """
        while True:
            email = input("Write a valid e-mail: ").strip()

            if not email:
                self.stdout.write(
                    self.style.ERROR("E-mail cannot be empty.")
                )
                continue

            user = User.objects.filter(email__iexact=email).first()

            if user is not None:
                self.stdout.write(
                    self.style.WARNING(
                        "\nA user with this e-mail already exists:\n"
                        f"  Username: {user.username}\n"
                        f"  E-mail:   {user.email}"
                    )
                )

                if self.ask_yes_no("Do you want to use this existing user?"):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Reusing existing user: {user.username}"
                        )
                    )
                    # Never request, set, reset, or send this user's password.
                    return user, False, None

                self.stdout.write(
                    "Enter another e-mail address to continue."
                )
                continue

            username = input("Write username: ").strip()

            if not username:
                self.stdout.write(
                    self.style.ERROR("Username cannot be empty.")
                )
                continue

            if User.objects.filter(username__iexact=username).exists():
                self.stdout.write(
                    self.style.ERROR(
                        "This username already exists. Choose another."
                    )
                )
                continue

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
                        self.style.ERROR("Passwords do not match.")
                    )
                    continue

                break

            user = User.objects.create_superuser(
                email=email,
                username=username,
                password=password,
            )

            # Mark the email as verified only if the custom field exists.
            if hasattr(user, "is_verified_email"):
                user.is_verified_email = True
                user.save(update_fields=["is_verified_email"])

            self.stdout.write(
                self.style.SUCCESS(
                    f"Superuser created successfully: {user.username}"
                )
            )
            return user, True, password

    @transaction.atomic
    def handle(self, *args, **options):
        user, user_created, password = self.get_or_create_bootstrap_user()

        # Do not silently elevate an existing account's privileges.
        # The user must explicitly approve promotion to superuser.
        if not user_created and not user.is_superuser:
            if self.ask_yes_no(
                "This existing user is not a superuser. "
                "Grant superuser privileges?"
            ):
                user.is_staff = True
                user.is_superuser = True
                user.save(update_fields=["is_staff", "is_superuser"])
                self.stdout.write(
                    self.style.SUCCESS("Superuser privileges granted.")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "Bootstrap cancelled: the selected user is not a "
                        "superuser. No password was changed."
                    )
                )
                return


        
        data = {
            "entity_type": "SaaS",
            "branch": "Main",
        }

        # 1. Entity type
        entity_type, _ = EntityType.objects.get_or_create(
            name=data["entity_type"],
            defaults={"state": "Active"},
        )
        if entity_type.state != "Active":
            entity_type.state = "Active"
            entity_type.save(update_fields=["state"])

        
        entity = Entity.objects.filter(
            entity_type=entity_type
        ).order_by('created_at', 'id').first()

        # 2. Entity
        entity, _ = Entity.objects.get_or_create(
            name=entity.name,
            entity_type=entity_type,
            defaults={"state": "Active"},
        )
        if entity.state != "Active":
            entity.state = "Active"
            entity.save(update_fields=["state"])

        # Link the user to the entity without duplicating the association.
        entity.admins.add(user)
        EntityUser.objects.get_or_create(
            user=user,
            entity=entity,
            defaults={"state": "Active"},
        )

        # 3. Branch
        branch, _ = Branch.objects.get_or_create(
            name=data["branch"],
            entity=entity,
            defaults={"state": "Active"},
        )
        if branch.state != "Active":
            branch.state = "Active"
            branch.save(update_fields=["state"])

        BranchUser.objects.get_or_create(
            user=user,
            branch=branch,
            defaults={"state": "Active"},
        )

        # 4. Groups and assignments
        for group_name in GROUPS:
            group, _ = Group.objects.get_or_create(name=group_name)

            BranchUserGroup.objects.get_or_create(
                user=user,
                branch=branch,
                group=group,
                defaults={"state": "Active"},
            )
            EntityTypeGroup.objects.get_or_create(
                entity_type=entity_type,
                group=group,
                defaults={"state": "Active"},
            )
            EntityGroup.objects.get_or_create(
                entity=entity,
                group=group,
                defaults={"state": "Active"},
            )
            BranchGroup.objects.get_or_create(
                branch=branch,
                group=group,
                defaults={"state": "Active"},
            )

        self.stdout.write(self.style.WARNING(""))

        # 5. Register and activate default applications/modules.
        for name in default_modules():
            app, _ = App.objects.get_or_create(
                name=name,
                defaults={"state": "Active"},
            )
            if app.state != "Active":
                app.state = "Active"
                app.save(update_fields=["state"])

            EntityTypeApp.objects.get_or_create(
                app=app,
                entity_type=entity_type,
                defaults={"state": "Active"},
            )

            entity_app, _ = EntityApp.objects.get_or_create(
                app=app,
                entity=entity,
                defaults={"state": "Active"},
            )
            if entity_app.state != "Active":
                entity_app.state = "Active"
                entity_app.save(update_fields=["state"])

            self.stdout.write(
                self.style.WARNING(f"✔ {'App:':20} {app.name}")
            )

        # 6. Load frontend and language defaults.
        FrontEndService.load_defaults(
            stdout=self.stdout,
            style=self.style,
        )
        LanguageService.load_defaults(
            stdout=self.stdout,
            style=self.style,
        )

        # Only send the password to the welcome-email service for a newly
        # created account. Never send or attempt to recover an existing user's
        # password.
        if user_created:
            email_sent = send_bootstrap_welcome_email(
                user,
                entity=entity,
                entity_type=entity_type,
                branch=branch,
                group="Root",
                password=password,
            )
            if email_sent:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✔ Welcome email sent to {user.email}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠ Welcome email was not sent "
                        "(no provider configured or send failed)."
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Welcome email skipped for the existing user. "
                    "The password was not changed."
                )
            )

        # 7. Summary
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("✔ SaaS bootstrap completed")
        )
        self.stdout.write(
            self.style.HTTP_INFO(f"{'Email:':20} {user.email}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"{'User:':20} {user.username}")
        )
        self.stdout.write(
            self.style.HTTP_INFO(f"{'EntityType:':20} {entity_type.name}")
        )
        self.stdout.write(
            self.style.HTTP_INFO(f"{'Entity:':20} {entity.name}")
        )
        self.stdout.write(
            self.style.HTTP_INFO(f"{'Branch:':20} {branch.name}")
        )
        self.stdout.write(
            self.style.WARNING(f"{'Groups:':20} {', '.join(GROUPS)}")
        )
        self.stdout.write(
            self.style.SUCCESS("✔ Groups and applications configured")
        )
        self.stdout.write(
            self.style.SUCCESS("✔ Frontend and language defaults loaded")
        )
        self.stdout.write(
            self.style.WARNING("⚠ Keep account credentials safe.")
        )
