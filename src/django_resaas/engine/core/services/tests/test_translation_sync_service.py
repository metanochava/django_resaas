import pytest

from django_resaas.engine.core.services.language_service import LanguageService
from django_resaas.engine.core.services.translation_sync_service import TranslationSyncService
from django_resaas.engine.models.language import Language
from django_resaas.engine.models.translation import Translation

pytestmark = pytest.mark.django_db


def test_sync_populates_translations_from_lang_modules():
    LanguageService.load_defaults()
    en = Language.objects.get(code="en-us")

    TranslationSyncService.sync()

    # a real key from django_resaas/lang/enus.py's key_value dict
    translation = Translation.objects.get(language=en, chave="Saúde")
    assert translation.translation == "Health"


def test_sync_is_idempotent_and_updates_changed_values():
    LanguageService.load_defaults()
    en = Language.objects.get(code="en-us")

    TranslationSyncService.sync()
    Translation.objects.filter(language=en, chave="Saúde").update(translation="stale")

    TranslationSyncService.sync()

    translation = Translation.objects.get(language=en, chave="Saúde")
    assert translation.translation == "Health"
