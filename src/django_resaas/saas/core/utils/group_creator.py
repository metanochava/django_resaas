import logging

logger = logging.getLogger(__name__)

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

    `revoke` (opcional, no mesmo dict): codenames que o perfil deixa de ter -
    a única forma de um ficheiro de perfis RETIRAR uma permissão (o resto é
    aditivo). Explícito e idempotente: só tira os codenames listados, uma
    segunda execução não muda nada. Um codename não pode estar em
    `permissions` e em `revoke` do mesmo perfil (ValueError).

    `rename_from`: dict opcional `{novo_nome: nome_antigo}` (ou uma lista
    de nomes antigos, por ordem de preferência) - renomeia
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

    # What happened, per run - returned to the caller and missing
    # codenames logged: a default permission that does not exist is never
    # created here, but it is never skipped silently either.
    report = {
        "groups_created": [],
        "groups_reused": [],
        "groups_renamed": [],
        "permissions_assigned": {},
        "permissions_already_assigned": {},
        "permissions_missing": {},
        "permissions_revoked": {},
    }

    # ------------------------------------------------------
    # 🔥 GARANTE EntityType BASE
    # ------------------------------------------------------
    entity_type, _ = EntityType.objects.get_or_create(
        name="SaaS",
        defaults={"state": "Active"}
    )

    # ------------------------------------------------------
    # 🔥 GARANTE Entity COM entity_type
    # ------------------------------------------------------
    entity, _ = Entity.objects.get_or_create(
        name="Tenant",
        entity_type=entity_type,  # 🔥 FIX CRÍTICO
        defaults={"state": "Active"}
    )

    # ------------------------------------------------------
    # 🔥 CRIA GRUPOS
    # ------------------------------------------------------
    for g in groups:
        if isinstance(g, dict):
            name = g["name"]
            permission_codenames = g.get("permissions") or []
            revoke_codenames = g.get("revoke") or []
        else:
            name = g
            permission_codenames = []
            revoke_codenames = []

        both = sorted(set(permission_codenames) & set(revoke_codenames))
        if both:
            raise ValueError(
                f"group_creator: profile '{name}' both grants and revokes: {', '.join(both)}"
            )

        # one old name or a list of them (e.g. the Portuguese name and a
        # later English one): the FIRST that exists is renamed in place
        old_names = rename_from.get(name) or []
        if isinstance(old_names, str):
            old_names = [old_names]

        if not Group.objects.filter(name=name).exists():
            for old_name in old_names:
                if Group.objects.filter(name=old_name).exists():
                    Group.objects.filter(name=old_name).update(name=name)
                    report["groups_renamed"].append((old_name, name))
                    break

        group, created = Group.objects.get_or_create(name=name)
        report["groups_created" if created else "groups_reused"].append(name)

        EntityTypeGroup.objects.get_or_create(
            entity_type=entity_type,
            group=group,
            defaults={"state": 'Active'}
        )

        EntityGroup.objects.get_or_create(
            entity=entity,
            group=group,
            defaults={"state": 'Active'}
        )

        if permission_codenames:
            perms = list(Permission.objects.filter(codename__in=permission_codenames))
            already = set(group.permissions.filter(
                codename__in=permission_codenames
            ).values_list("codename", flat=True))
            found = {perm.codename for perm in perms}
            missing = sorted(set(permission_codenames) - found)

            group.permissions.add(*perms)

            report["permissions_assigned"][name] = sorted(found - already)
            report["permissions_already_assigned"][name] = sorted(already)

            if missing:
                report["permissions_missing"][name] = missing
                logger.warning(
                    "group_creator: profile '%s' expects permissions that do not exist "
                    "(not created, not assigned): %s",
                    name,
                    ", ".join(missing),
                )

        if revoke_codenames:
            revoked = list(group.permissions.filter(codename__in=revoke_codenames))
            group.permissions.remove(*revoked)
            report["permissions_revoked"][name] = sorted(p.codename for p in revoked)

    return report
