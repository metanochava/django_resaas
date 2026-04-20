from django_resaas.models.idioma import Idioma
from django.db import IntegrityError
class IdiomaService:
    """
    Serviço responsável por inicializar os idiomas base do sistema.
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

        out(f"\n 🌍 Idiomas padrão", style.MIGRATE_HEADING if style else None)

        for nome, code in cls.DEFAULT_IDIOMAS:

            # 🔥 normalizar
            code = code.lower().strip()

            try:
                idioma, created = Idioma.objects.get_or_create(
                    code=code,
                    defaults={
                        "nome": nome,
                        "estado": 1
                    }
                )
            except IntegrityError:
                # 🔥 fallback seguro
                idioma = Idioma.objects.get(code=code)
                created = False

            if created:
                out(f"✔ Idioma criado:\t {idioma.nome} ({idioma.code})",
                    style.SUCCESS if style else None)
            else:
                out(f"✔ Idioma existente:\t {idioma.nome} ({idioma.code})",
                    style.WARNING if style else None)