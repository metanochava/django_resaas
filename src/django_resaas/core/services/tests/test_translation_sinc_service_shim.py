"""
translation_sinc_service.py (typo'd name) is kept as a backward-compat
shim over translation_sync_service.py - this locks in that old imports
keep working.
"""
def test_old_typo_module_path_still_importable():
    from django_resaas.core.services.translation_sinc_service import (
        TranslationSyncService as OldPath,
    )
    from django_resaas.core.services.translation_sync_service import (
        TranslationSyncService as NewPath,
    )

    assert OldPath is NewPath
