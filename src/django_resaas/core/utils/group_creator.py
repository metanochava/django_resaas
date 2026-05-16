GROUPS = [
"Guest",
"Admin",
"Root",
]

def group_creator(groups=None):
    if groups is None:
        groups = []

    # 🔥 IMPORT LAZY
    from django_resaas.models.group import Group
    from django_resaas.models.entity_type import EntityType
    from django_resaas.models.entity import Entity
    from django_resaas.models.entity_type_group import EntityTypeGroup
    from django_resaas.models.entity_group import EntityGroup

    # ------------------------------------------------------
    # 🔥 GARANTE EntityType BASE
    # ------------------------------------------------------
    entity_type, _ = EntityType.objects.get_or_create(
        name="SaaS",
        estado= 1
    )

    # ------------------------------------------------------
    # 🔥 GARANTE Entity COM entity_type
    # ------------------------------------------------------
    entity, _ = Entity.objects.get_or_create(
        name="Tenant",
        entity_type=entity_type,  # 🔥 FIX CRÍTICO
        estado= 1
    )

    # ------------------------------------------------------
    # 🔥 CRIA GRUPOS
    # ------------------------------------------------------
    for g in groups:
        group, _ = Group.objects.get_or_create(name=g)

        EntityTypeGroup.objects.get_or_create(
            entity_type=entity_type,
            group=group,
            defaults={"estado": 1}
        )

        EntityGroup.objects.get_or_create(
            entity=entity,
            group=group,
            defaults={"estado": 1}
        )



