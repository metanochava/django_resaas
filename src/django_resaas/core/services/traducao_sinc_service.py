import importlib

from django.apps import apps
from django_resaas.models.idioma import Idioma
from django_resaas.models.traducao import Traducao


class TraducaoSyncService:
    """
    Sincroniza traduções a partir de módulos app.lang.<idioma>
    para a base de dados.
    """

    @classmethod
    def sync(cls, stdout=None, style=None):
        idiomas = Idioma.objects.all()

        for idioma in idiomas:
            lang_code = idioma.code.lower().replace("-", "")

            if stdout:
                stdout.write(
                    style.MIGRATE_HEADING(
                        f"\n🌍 Sincronizando idioma: {idioma.nome} ({lang_code})"
                    )
                )

            for app in apps.get_app_configs():
                module_name = f"{app.name}.lang.{lang_code}"

                try:
                    module = importlib.import_module(module_name)
                except ModuleNotFoundError:
                    continue

                if not hasattr(module, "key_value"):
                    continue

                cls._sync_module(
                    idioma,
                    module.key_value,
                    app.label,
                    stdout,
                    style
                )

    @staticmethod
    def _sync_module(idioma, traducoes, app_label, stdout=None, style=None):
        for chave, traducao in traducoes.items():
            obj, created = Traducao.objects.get_or_create(
                idioma=idioma,
                chave=chave,
                defaults={"traducao": traducao}
            )

            if not created and obj.traducao != traducao:
                obj.traducao = traducao
                obj.save(update_fields=["traducao"])

                if stdout:
                    stdout.write(
                        style.SUCCESS(
                            f"🔁 Atualizada [{app_label}]: {chave}"
                        )
                    )
            elif created:
                if stdout:
                    stdout.write(
                        style.SUCCESS(
                            f"✔ Criada [{app_label}]: {chave}"
                        )
                    )
            else:
                if stdout:
                    stdout.write(
                        style.WARNING(
                            f"✔ Existente [{app_label}]: {chave}"
                        )
                    )
