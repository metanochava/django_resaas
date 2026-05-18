from django_resaas.models.language import Language
from django.db import IntegrityError


class LanguageService:
    """
    Serviço responsável por inicializar os languages base do sistema.
    """

    DEFAULT_IDIOMAS = [
        ("Português", "pt-pt"),
        ("English", "en-us"),
        ("Español", "es-es"),
        ("Français", "fr-fr"),
    ]



    @classmethod
    def load_defaults(cls, stdout=None, style=None):

        def out(msg, sty=None):
            if stdout:
                stdout.write(sty(msg) if sty else msg)

        out(f"\n 🌍 Languages padrão", style.MIGRATE_HEADING if style else None)

        for name, code in cls.DEFAULT_IDIOMAS:

            # 🔥 normalizar
            code = code.lower().strip()

            try:
                language, created = Language.objects.get_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "state": 1
                    }
                )
            except IntegrityError:
                # 🔥 fallback seguro
                language = Language.objects.get(code=code)
                created = False

            if created:
                out(f"✔ Language criado:\t {language.name} ({language.code})",
                    style.SUCCESS if style else None)
            else:
                out(f"✔ Language existente:\t {language.name} ({language.code})",
                    style.WARNING if style else None)