from django_resaas.models.traducao import Traducao
from django_resaas.models.idioma import Idioma


class TraducaoService:
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
            "Seleccione a Entidade": "Seleccione a Entidade",
            "Seleccione a Sucursal": "Seleccione a Sucursal",
            "Seleccione o Grupo": "Seleccione o Grupo",
        },
        "en-us": {
            "Login efectuado com sucesso": "Login successful",
            "Credenciais inválidas": "Invalid credentials",
            "Conta desactivada": "Account disabled",
            "Email não verificado": "Email not verified",
            "Configuração inicial criada com sucesso": "Initial setup completed successfully",
            "Seleccione a Entidade": "Select Entity",
            "Seleccione a Sucursal": "Select Branch",
            "Seleccione o Grupo": "Select Group",
        },
    }

    @classmethod
    def load_defaults(cls, stdout=None, style=None):
        for code, traducoes in cls.DEFAULT_TRADUCOES.items():
            try:
                idioma = Idioma.objects.get(code=code)
            except Idioma.DoesNotExist:
                if stdout:
                    stdout.write(
                        style.ERROR(f"✖ Idioma não encontrado: {code}")
                    )
                continue

            if stdout:
                stdout.write(
                    style.MIGRATE_HEADING(f"\n🌐 Idioma: {idioma.nome}")
                )

            for chave, traducao in traducoes.items():
                obj, created = Traducao.objects.get_or_create(
                    idioma=idioma,
                    chave=chave,
                    defaults={"traducao": traducao}
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
