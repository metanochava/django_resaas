from django.db.models.signals import post_migrate
from django.dispatch import receiver

from django_resaas.core.base.registry import VIEW_REGISTRY
from django_resaas.core.services.action_sync_service import ActionSyncService


@receiver(post_migrate)
def sync_resaas_actions(sender, **kwargs):
    """
    Sincroniza todas as @resaas_action registadas nas Views.

    Executa após as migrations para garantir que:
    - ModelExtraAction já existe
    - auth_permission já existe
    - django_content_type já existe

    Faz:
    - INSERT de novas actions
    - UPDATE de actions alteradas
    - DELETE de actions removidas
    - cria/remove Permissions geridas pelo RESAAS
    """

    if not VIEW_REGISTRY:
        return

    ActionSyncService.sync_registry(
        VIEW_REGISTRY
    )