# Deprecated: this module name has a typo ("sinc" -> "sync"). The real
# implementation now lives in translation_sync_service.py; this module is
# kept only so external code importing from the old path keeps working.
from django_resaas.engine.core.services.translation_sync_service import (  # noqa: F401
    TranslationSyncService,
)
