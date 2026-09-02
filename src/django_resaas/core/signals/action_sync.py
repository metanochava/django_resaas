from django.contrib.contenttypes.models import ContentType
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

    `ContentType.objects.clear_cache()` primeiro: este receiver não é
    filtrado por app (ao contrário de `create_model_permissions`), por
    isso corre em TODO `post_migrate` - incluindo o disparado por
    `flush` (ex.: teardown de um `TransactionTestCase`/
    `pytest.mark.django_db(transaction=True)`), que apaga e recria a
    tabela `django_content_type`. Sem limpar a cache em memória do
    `ContentTypeManager`, `ContentType.objects.get_for_model()` pode
    devolver um objecto com um `id` de ANTES do flush, e o
    `Permission.objects.get_or_create(content_type=...)` que se segue
    falha com "FOREIGN KEY constraint failed" ao fazer commit -
    reproduzível de forma determinística sempre que VIEW_REGISTRY tem
    modelos suficientes para tornar a janela de cache obsoleta visível
    (foi assim que apareceu ao adicionar as views de notifications).
    """

    if not VIEW_REGISTRY:
        return

    ContentType.objects.clear_cache()

    ActionSyncService.sync_registry(VIEW_REGISTRY)
