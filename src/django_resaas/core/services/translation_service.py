from django_resaas.models.translation import Translation
from django_resaas.models.language import Language


class TranslationService:
    """
    Serviço para carga inicial de traduções base do sistema
    """

    DEFAULT_TRADUCOES = {
        "pt-pt": {
            "Login efectuado com sucesso": "Login efectuado com sucesso",
            "Credenciais inválidas": "Credenciais inválidas",
            "Conta desactivada": "Conta desactivada",
            "Email não verificado": "Email não verificado",
            "Configuração inicial criada com sucesso": "Configuração inicial criada com sucesso",
            "Seleccione a Entity": "Seleccione a Entity",
            "Seleccione a Branch": "Seleccione a Branch",
            "Seleccione o Group": "Seleccione o Group",
        },
        "en-us": {
            "Login efectuado com sucesso": "Login successful",
            "Credenciais inválidas": "Invalid credentials",
            "Conta desactivada": "Account disabled",
            "Email não verificado": "Email not verified",
            "Configuração inicial criada com sucesso": "Initial setup completed successfully",
            "Seleccione a Entity": "Select Entity",
            "Seleccione a Branch": "Select Branch",
            "Seleccione o Group": "Select Group",
        },
    }

    @classmethod
    def load_defaults(cls, stdout=None, style=None):
        for code, traducoes in cls.DEFAULT_TRADUCOES.items():
            try:
                language = Language.objects.get(code=code)
            except Language.DoesNotExist:
                if stdout:
                    stdout.write(
                        style.ERROR(f"✖ Language não encontrado: {code}")
                    )
                continue

            if stdout:
                stdout.write(
                    style.MIGRATE_HEADING(f"\n🌐 Language: {language.name}")
                )

            for chave, translation in traducoes.items():
                obj, created = Translation.objects.get_or_create(
                    language=language,
                    chave=chave,
                    defaults={"translation": translation}
                )

                if stdout:
                    if created:
                        stdout.write(
                            style.SUCCESS(f"✔ {chave}")
                        )
                    else:
                        stdout.write(
                            style.WARNING(f"✔  {chave}")
                        )

        return True
