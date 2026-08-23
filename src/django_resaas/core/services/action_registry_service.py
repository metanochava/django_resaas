from django_resaas.core.base.registry import VIEW_REGISTRY
from django_resaas.core.services.action_sync_service import ActionSyncService


class ActionRegistryService:

    @classmethod
    def sync(cls):
        """
        Sincroniza todas as @resaas_action declaradas
        nas Views registadas no VIEW_REGISTRY.
        """

        ActionSyncService.sync_registry(
            VIEW_REGISTRY
        )