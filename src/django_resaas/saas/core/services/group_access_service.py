"""Who may see and change a Group (GroupAPIView, PermissionAPIView).

Group rows are GLOBAL: the same group can be linked to several Entities
(EntityGroup) and be an EntityType template (EntityTypeGroup), so changing it
changes it everywhere it is linked.

- Platform level = the change_entitytype permission (held by Root by default).
  It sees and changes every group. Never decided by a group's name.
- Otherwise a caller only SEES the groups linked to the current Entity, and
  only CHANGES one that belongs to the current Entity, is editable (created by
  the Entity for itself) and is not shared with another Entity nor a template.
- Nobody grants or revokes a permission their active group doesn't hold.

All checks use the signed request context (check_permission), never ids from
the request body.
"""
from rest_framework import status

from django_resaas.saas.core.base.permissions import isPermited
from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_type_group import EntityTypeGroup

PLATFORM_PERMISSION = "change_entitytype"


def require_permission(request, codename):
    if not isPermited(request=request, role=codename):
        raise ResaasAPIException(
            "Permission denied",
            code="permission_denied",
            status_code=status.HTTP_403_FORBIDDEN,
        )


def is_platform(request):
    return isPermited(request=request, role=PLATFORM_PERMISSION)


def visible_groups(request, queryset):
    """Every group at platform level; otherwise the current Entity's groups."""

    if is_platform(request):
        return queryset

    return queryset.filter(entitygroup__entity_id=request.entity_id).distinct()


def check_group_changeable(request, group):
    """Raises unless the caller may change `group` (see module docstring)."""

    if is_platform(request):
        return

    links = EntityGroup.objects.filter(group_id=group.id)

    if not links.filter(entity_id=request.entity_id).exists():
        raise ResaasAPIException(
            "This profile does not belong to the current entity.",
            code="group_not_in_entity",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if not group.editable:
        raise ResaasAPIException(
            "This profile is not editable and can only be changed at platform level.",
            code="group_not_editable",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    shared = (
        links.exclude(entity_id=request.entity_id).exists()
        or EntityTypeGroup.objects.filter(group_id=group.id).exists()
    )

    if shared:
        raise ResaasAPIException(
            "This profile is shared with other entities and can only be changed at platform level.",
            code="group_shared",
            status_code=status.HTTP_403_FORBIDDEN,
        )


def held_codenames(request):
    """Codenames of the caller's ACTIVE group in the current signed context -
    the same membership check_permission() resolves."""

    return set(
        BranchUserGroup.objects.filter(
            user=request.user,
            group_id=request.group_id,
            branch_id=request.branch_id,
            branch__entity_id=request.entity_id,
            branch__entity__entity_type_id=request.entity_type_id,
        ).values_list("group__permissions__codename", flat=True)
    ) - {None}


def check_delegation(request, changed_permissions):
    """No privilege escalation by delegation: every permission being granted
    or revoked must be held by the caller's active group."""

    held = held_codenames(request)
    not_held = sorted(
        str(permission.id)
        for permission in changed_permissions
        if permission.codename not in held
    )

    if not_held:
        raise ResaasAPIException(
            "You cannot grant or revoke permissions you do not have.",
            code="permission_not_held",
            details={"permissions": not_held},
            status_code=status.HTTP_403_FORBIDDEN,
        )
