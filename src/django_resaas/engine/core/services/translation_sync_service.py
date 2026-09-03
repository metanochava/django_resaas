import importlib

from django.apps import apps
from django_resaas.engine.models.language import Language
from django_resaas.engine.models.translation import Translation


class TranslationSyncService:
    """
    Sincroniza traduções a partir de módulos app.lang.<language>
    para a base de dados.
    """

    @classmethod
    def sync(cls, stdout=None, style=None):
        languages = Language.objects.all()

        for language in languages:
            lang_code = language.code.lower().replace("-", "")

            if stdout:
                stdout.write(
                    style.MIGRATE_HEADING(
                        f"\n🌍 Syncing language: {language.name} ({lang_code})"
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
                    language,
                    module.key_value,
                    app.label,
                    stdout,
                    style
                )

    @staticmethod
    def _sync_module(language, traducoes, app_label, stdout=None, style=None):
        for chave, translation in traducoes.items():
            obj, created = Translation.objects.get_or_create(
                language=language,
                chave=chave,
                defaults={"translation": translation}
            )

            if not created and obj.translation != translation:
                obj.translation = translation
                obj.save(update_fields=["translation"])

                if stdout:
                    stdout.write(
                        style.SUCCESS(
                            f"🔁 Updated [{app_label}]: {chave}"
                        )
                    )
            elif created:
                if stdout:
                    stdout.write(
                        style.SUCCESS(
                            f"✔ Created [{app_label}]: {chave}"
                        )
                    )
            else:
                if stdout:
                    stdout.write(
                        style.WARNING(
                            f"✔ Already exists [{app_label}]: {chave}"
                        )
                    )
