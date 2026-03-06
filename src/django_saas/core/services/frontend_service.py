import secrets
from django_saas.models.front_end import FrontEnd


class FrontEndService:
    """
    Serviço para registar FrontEnds autorizados (Web, Mobile, etc)
    """

    DEFAULT_FRONTENDS = [
        {
            "nome": "Quasar Web",
            "fek": "frontend.quasar",
            "access": "super",
        },
    ]

    @classmethod
    def generate_secret(cls):
        return secrets.token_urlsafe(25)

    @classmethod
    def load_defaults(cls, stdout=None, style=None):
        for item in cls.DEFAULT_FRONTENDS:
            frontend, created = FrontEnd.objects.get_or_create(
                fek=item["fek"],
                defaults={
                    "nome": item["nome"],
                    "fep": cls.generate_secret(),
                    "access": item.get("access", "read"),
                    "estado": 1,
                }
            )

            if stdout:
                if created:
                    stdout.write(
                        style.SUCCESS(f"\n✔ FrontEnd criado: {frontend.nome}")
                    )
                    stdout.write(
                        style.NOTICE(f"  FEK: {frontend.fek}")
                    )
                    stdout.write(
                        style.WARNING(f"  FEP: {frontend.fep}")
                    )
                else:
                    stdout.write(
                        style.WARNING(f"\nFrontEnd já existe: {frontend.nome}")
                    )
                    stdout.write(
                        style.NOTICE(f"  FEK: {frontend.fek}")
                    )
                    stdout.write(
                        style.WARNING(f"  FEP: {frontend.fep}")
                    )

        return True
