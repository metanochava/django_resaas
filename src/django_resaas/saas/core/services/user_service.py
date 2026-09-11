import getpass
from django.contrib.auth import get_user_model

User = get_user_model()


class UserService:

    @staticmethod
    def get_or_create_superuser(stdout=None, style=None):
        email = input("Enter the email: ")
        username = input("Enter the username: ")
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
                password = getpass.getpass("🔐 Superuser password: ")
                password_confirm = getpass.getpass("Confirm the password: ")

                if not password:
                    if stdout and style:
                        stdout.write(
                            style.ERROR("Password cannot be empty")
                        )
                    continue

                if password != password_confirm:
                    if stdout and style:
                        stdout.write(
                            style.ERROR("Passwords do not match")
                        )
                    continue

                break
            user.set_password(password)
            user.save()
        else:
            if stdout and style:
                stdout.write(
                    style.WARNING("✔  Superuser already exists \n ")
                )
                stdout.write(style.WARNING(f"✉️ Email: \t {user.email}"))
                stdout.write(style.SUCCESS(f"👤Username: \t {user.username} \n"))

        return user
