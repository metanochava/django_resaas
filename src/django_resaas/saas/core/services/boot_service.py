"""The sign-in boot in ONE answer (POST resaas/boot/).

After signing in the frontend used to walk Entity -> Branch -> Group one
request at a time: userEntitys/, a context for the Entity, me/, userBranchs/,
a context for the Branch, userGroups/, a context for the Group, permissions/,
menus/, mobile_tabs/ - about ten round trips in series, several of them
repeated. This answers all of it at once, with the same rules:

- the Entities are the user's (admin or member), narrowed to the host's
  EntityType (`entity_type_name`, as userEntitys/ does);
- a choice is made only when there is nothing to ask: the hint the frontend
  sends (the user's last choice on that site) when it is still allowed, else
  the only option (for profiles: the only working one besides Guest -
  GroupStore.singleWorkingGroup);
- only Active profile assignments count (BranchUserGroup.state);
- the context token is issued by ResaasContextService.issue (its own entity,
  branch and group validation), and the permissions, menus and phone tabs are
  those of that context (core/menus.build_menus, mobile_tab_service.tabs_for).

When a choice remains, the answer stops there (`entity`, `branch` or `group`
is null) with the options to choose from and the context of what was chosen.
"""
from types import SimpleNamespace

from django.db.models import Q

from django_resaas.saas.core.tenant.context import ResaasContextService

GUEST = "Guest"


def entities_of(user, entity_type_name=None):
    from django_resaas.saas.models.entity import Entity
    from django_resaas.saas.models.entity_type import EntityType

    entities = Entity.objects.filter(
        Q(admins=user) | Q(entityuser__user=user, entityuser__deleted_at__isnull=True)
    ).select_related("entity_type").distinct().order_by("name")

    # a name that is no EntityType (the "app" of app.example.com) filters nothing
    name = str(entity_type_name or "").strip()
    if name and EntityType.objects.filter(name__iexact=name).exists():
        entities = entities.filter(entity_type__name__iexact=name)
    return entities


def entity_rows(request, entities):
    """The shape of users/{id}/userEntitys/ (the frontend stores it as is)."""
    from django_resaas.saas.data.entity.serializers.entity import EntitySerializer

    rows = []
    for entity in entities:
        data = EntitySerializer(entity, context={"request": request}).data
        rows.append({
            "id": data["id"],
            # entity_type is what every consumer reads; entityType is the old
            # key, kept for compatibility (DEPRECATED)
            "entity_type": data["entity_type"],
            "entityType": data["entity_type"],
            "name": data["name"],
            "dashboard": data["dashboard"],
            "created_at": data["created_at"].split("-")[0] if data.get("created_at") else None,
            "logo": data.get("logo"),
            "site": data.get("site"),
        })
    return rows


def branch_rows(user, entity):
    from django_resaas.saas.models.branch_user import BranchUser

    links = (BranchUser.objects
             .filter(user=user, branch__entity=entity)
             .select_related("branch").order_by("branch__name"))
    return [{"id": str(link.branch.id), "name": link.branch.name} for link in links]


def group_rows(user, branch_id):
    from django_resaas.saas.models.branch_user_group import ACTIVE, BranchUserGroup

    links = (BranchUserGroup.objects
             .filter(user=user, branch_id=branch_id, state=ACTIVE)
             .select_related("group").order_by("group__name"))
    return [{"id": str(link.group.id), "name": link.group.name, "state": link.state} for link in links]


def _by_id(rows, hint):
    return next((row for row in rows if hint and str(row["id"]) == str(hint)), None)


def pick(rows, hint=None):
    return _by_id(rows, hint) or (rows[0] if len(rows) == 1 else None)


def pick_group(rows, hint=None):
    """The hint, else the only profile, else the only working one besides Guest."""
    chosen = _by_id(rows, hint)
    if chosen:
        return chosen
    if len(rows) == 1:
        return rows[0]
    working = [row for row in rows if row["name"] != GUEST]
    return working[0] if len(working) == 1 and len(working) == len(rows) - 1 else None


def boot(request, data):
    from django_resaas.saas.core.menus import build_menus
    from django_resaas.saas.core.services.mobile_tab_service import tabs_for
    from django_resaas.saas.models.group import Group

    user = request.user
    entities = list(entities_of(user, data.get("entity_type_name")))
    rows = entity_rows(request, entities)
    answer = {
        "entities": rows, "entity": None,
        "branches": None, "branch": None,
        "groups": None, "group": None,
        "context": None, "permissions": None, "menus": None, "mobile_tabs": None,
    }

    entity_row = pick(rows, data.get("entity_id"))
    if entity_row is None:
        return answer
    entity = next(item for item in entities if str(item.id) == str(entity_row["id"]))
    answer["entity"] = entity_row

    answer["branches"] = branch_rows(user, entity)
    branch = pick(answer["branches"], data.get("branch_id"))
    if branch is None:
        answer["context"] = ResaasContextService.issue(user=user, entity_id=entity.id)
        return answer
    answer["branch"] = branch

    answer["groups"] = group_rows(user, branch["id"])
    group = pick_group(answer["groups"], data.get("group_id"))
    if group is None:
        answer["context"] = ResaasContextService.issue(user=user, entity_id=entity.id, branch_id=branch["id"])
        return answer
    answer["group"] = group

    answer["context"] = ResaasContextService.issue(
        user=user, entity_id=entity.id, branch_id=branch["id"], group_id=group["id"],
    )
    # what the next requests will see with that context (as the middleware sets it)
    scope = SimpleNamespace(
        user=user, entity_type_id=str(entity.entity_type_id), entity_id=str(entity.id),
        branch_id=branch["id"], group_id=group["id"],
    )
    answer["permissions"] = sorted(
        Group.objects.get(id=group["id"]).permissions.values_list("codename", flat=True)
    )
    answer["menus"] = build_menus(scope)
    answer["mobile_tabs"] = tabs_for(scope)
    return answer
