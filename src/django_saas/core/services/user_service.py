import getpass
from django.contrib.auth import get_user_model

User = get_user_model()


class UserService:

    @staticmethod
    def get_or_create_superuser(stdout=None, style=None):
        email = input("Digite o email: ")
        username = input("Digite o username: ")
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                'is_verified_email': True,
                "is_staff": True,
                "is_superuser": False,
            }
        )

        if created:
            # 🔐 pedir password pelo teclado (sem mostrar)
            while True:
                password = getpass.getpass("🔐 Password do superuser: ")
                password_confirm = getpass.getpass("Confirme a password: ")

                if not password:
                    self.stdout.write(
                        self.style.ERROR("A password não pode estar vazia")
                    )
                    continue

                if password != password_confirm:
                    self.stdout.write(
                        self.style.ERROR("As passwords não coincidem")
                    )
                    continue

                break
            user.set_password(password)
            user.save()
        else:
            if stdout and style:
                stdout.write(
                    style.WARNING("✔  Superuser já existe \n ")
                )
                stdout.write(style.WARNING(f"✉️ Email: \t {user.email}"))
                stdout.write(style.SUCCESS(f"👤Username: \t {user.username} \n"))

        return user
