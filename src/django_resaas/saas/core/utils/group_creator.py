GROUPS = [
"Guest",
"Admin",
"Root",
]


def group_creator(groups=None, rename_from=None):
    """
    Cria (idempotente) os Group "perfil" de um módulo, como templates
    ligados a EntityType/Entity - mecanismo de referência usado por
    saude/apps.py, replicado por sales/inventory/farmacia's apps.py.

    `groups`: lista de nomes (str, retrocompatível) OU de dicts
    `{"name": str, "permissions": [codename, ...]}` - quando um item
    tem `permissions`, essas Permission (codenames REAIS já existentes,
    nunca inventados aqui) são concedidas ao Group (aditivo - nunca
    remove permissões já lá postas manualmente por um admin).

    `rename_from`: dict opcional `{novo_nome: nome_antigo}` - renomeia
    em vez de criar duplicado quando o Group antigo já existir (ex.:
    migração de nomes em português para inglês). `Group.id` é a PK
    real (UUID) e todas as relações - BranchUserGroup, EntityGroup,
    permissions - apontam para `id`, nunca para `name`; renomear o
    `name` no lugar preserva tudo. Sem efeito (fica apenas o
    get_or_create normal a seguir) quando o Group antigo não existe -
    seguro tanto numa instalação já em produção como numa nova.
    """
    if groups is None:
        groups = []

    # 🔥 IMPORT LAZY
    from django.contrib.auth.models import Permission

    from django_resaas.saas.models.group import Group
    from django_resaas.saas.models.entity_type import EntityType
    from django_resaas.saas.models.entity import Entity
    from django_resaas.saas.models.entity_type_group import EntityTypeGroup
    from django_resaas.saas.models.entity_group import EntityGroup

    rename_from = rename_from or {}

    # ------------------------------------------------------
    # 🔥 GARANTE EntityType BASE
    # ------------------------------------------------------
    entity_type, _ = EntityType.objects.get_or_create(
        name="SaaS",
        state= 1
    )

    # ------------------------------------------------------
    # 🔥 GARANTE Entity COM entity_type
    # ------------------------------------------------------
    entity, _ = Entity.objects.get_or_create(
        name="Tenant",
        entity_type=entity_type,  # 🔥 FIX CRÍTICO
        state= 1
    )

    # ------------------------------------------------------
    # 🔥 CRIA GRUPOS
    # ------------------------------------------------------
    for g in groups:
        if isinstance(g, dict):
            name = g["name"]
            permission_codenames = g.get("permissions") or []
        else:
            name = g
            permission_codenames = []

        old_name = rename_from.get(name)

        if (
            old_name
            and not Group.objects.filter(name=name).exists()
            and Group.objects.filter(name=old_name).exists()
        ):
            Group.objects.filter(name=old_name).update(name=name)

        group, _ = Group.objects.get_or_create(name=name)

        EntityTypeGroup.objects.get_or_create(
            entity_type=entity_type,
            group=group,
            defaults={"state": 1}
        )

        EntityGroup.objects.get_or_create(
            entity=entity,
            group=group,
            defaults={"state": 1}
        )

        if permission_codenames:
            perms = Permission.objects.filter(codename__in=permission_codenames)
            group.permissions.add(*perms)
