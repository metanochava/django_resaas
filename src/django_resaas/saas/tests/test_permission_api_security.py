"""PermissionAPIView (auth/permissions/) and the removed model_data endpoint.

- Catalogue writes (create/update/destroy of Permission rows) need
  add/change/delete_permission; reading the catalogue needs authentication.
- setGroupPermissions needs change_group; without change_entitytype (platform
  level, Root) the group must belong to the current Entity, be editable and
  not be shared/template, because a Group row is global; nobody grants or
  revokes a permission they don't hold.
- addToGroup/removeFromGroup/addToUser/removeFromUser and
  resaasapps/<app>/<model>/data/ no longer exist.
"""
import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from django_resaas.saas.core.tenant.context import ResaasContextService
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_type_group import EntityTypeGroup
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.group import Group
from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db

SET_URL = "/api/auth/permissions/setGroupPermissions/"


def _perms(*codenames):
    return list(Permission.objects.filter(codename__in=codenames))


def _entity_group(tenant, name, editable=True):
    group = Group.objects.create(name=name, editable=editable)
    EntityGroup.objects.create(entity=tenant["entity"], group=group, state="Active")
    return group


def _actor(tenant, username, *codenames):
    """A non-Root user acting with a group that holds exactly `codenames`."""
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="pass-12345")
    EntityUser.objects.get_or_create(user=user, entity=tenant["entity"])
    BranchUser.objects.get_or_create(user=user, branch=tenant["branch"])
    group = _entity_group(tenant, f"{username}-group")
    group.permissions.set(_perms(*codenames))
    BranchUserGroup.objects.create(user=user, group=group, branch=tenant["branch"])

    context = ResaasContextService.issue(
        user=user, entity_id=tenant["entity"].id, branch_id=tenant["branch"].id, group_id=group.id
    )
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")
    return client


def _set(client, group, *permissions):
    return client.post(
        SET_URL, {"group": str(group.id), "permissions": [p.id for p in permissions]}, format="json"
    )


def _codenames(group):
    return set(group.permissions.values_list("codename", flat=True))


# ------------------------------------------------------------------ removed endpoints

def test_model_data_endpoint_no_longer_exists(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-model-data")
    tenant["client"].raise_request_exception = False

    response = tenant["client"].get("/api/django_resaas/resaasapps/django_resaas/User/data/")

    assert response.status_code == 404


@pytest.mark.parametrize("action", ["addToGroup", "removeFromGroup", "addToUser", "removeFromUser"])
def test_unscoped_relation_actions_no_longer_exist(bootstrap_tenant, action):
    tenant = bootstrap_tenant(f"pa-removed-{action.lower()}")
    tenant["client"].raise_request_exception = False
    permission = Permission.objects.get(codename="view_contract")

    response = tenant["client"].post(
        f"/api/auth/permissions/{permission.id}/{action}/", {"id": str(tenant["root_group"].id)}, format="json"
    )

    assert response.status_code == 404
    assert permission not in tenant["root_group"].permissions.filter(codename="__none__")


# ------------------------------------------------------------------ catalogue writes

def test_catalogue_can_be_read_by_an_authenticated_member(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-read")
    client = _actor(tenant, "pa-reader")

    assert client.get("/api/auth/permissions/").status_code == 200


def test_catalogue_writes_need_their_permission(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-write-denied")
    client = _actor(tenant, "pa-writer")
    permission = Permission.objects.get(codename="view_contract")

    create = client.post("/api/auth/permissions/", {
        "name": "Can hack", "codename": "hack_everything",
        "content_type": ContentType.objects.get_for_model(Group).id,
    }, format="json")
    rename = client.patch(f"/api/auth/permissions/{permission.id}/", {"name": "x"}, format="json")
    delete = client.delete(f"/api/auth/permissions/{permission.id}/")

    for response in (create, rename, delete):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "permission_denied"

    assert Permission.objects.filter(codename="view_contract").exists()
    assert not Permission.objects.filter(codename="hack_everything").exists()


def test_catalogue_delete_is_allowed_with_delete_permission(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-write-ok")
    client = _actor(tenant, "pa-deleter", "delete_permission")
    throwaway = Permission.objects.create(
        codename="throwaway_perm", name="Throwaway", content_type=ContentType.objects.get_for_model(Group)
    )

    response = client.delete(f"/api/auth/permissions/{throwaway.id}/")

    assert response.status_code in (200, 204)
    assert not Permission.objects.filter(id=throwaway.id).exists()


# ------------------------------------------------------------------ setGroupPermissions

def test_set_group_permissions_needs_change_group(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-set-denied")
    client = _actor(tenant, "pa-noperm", "view_contract")
    target = _entity_group(tenant, "Nurse")

    response = _set(client, target, *_perms("view_contract"))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
    assert _codenames(target) == set()


def test_exclusive_group_gets_permissions_the_actor_holds(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-set-ok")
    client = _actor(tenant, "pa-manager", "change_group", "view_contract")
    target = _entity_group(tenant, "Nurse")

    response = _set(client, target, *_perms("view_contract"))

    assert response.status_code == 200, response.json()
    assert _codenames(target) == {"view_contract"}


def test_actor_cannot_grant_a_permission_they_do_not_hold(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-escalate")
    client = _actor(tenant, "pa-escalator", "change_group", "view_contract")
    target = _entity_group(tenant, "Nurse")

    response = _set(client, target, *_perms("view_contract", "view_contract_salary"))

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "permission_not_held"
    assert error["details"]["permissions"] == [str(p.id) for p in _perms("view_contract_salary")]
    assert _codenames(target) == set()


def test_actor_cannot_grant_their_own_group_more(bootstrap_tenant):
    """The classic escalation: add a permission to the group you act with."""
    tenant = bootstrap_tenant("pa-self")
    client = _actor(tenant, "pa-self-actor", "change_group")
    own = Group.objects.get(name="pa-self-actor-group")

    response = _set(client, own, *_perms("change_group", "delete_permission"))

    assert response.status_code == 403
    assert _codenames(own) == {"change_group"}


def test_actor_cannot_revoke_a_permission_they_do_not_hold(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-revoke")
    client = _actor(tenant, "pa-revoker", "change_group")
    target = _entity_group(tenant, "Nurse")
    target.permissions.set(_perms("view_contract_salary"))

    response = _set(client, target)

    assert response.status_code == 403
    assert _codenames(target) == {"view_contract_salary"}


def test_unchanged_permissions_the_actor_lacks_are_not_a_grant(bootstrap_tenant):
    """The screen sends the whole list back: keeping a permission the actor
    doesn't hold is not granting it."""
    tenant = bootstrap_tenant("pa-unchanged")
    client = _actor(tenant, "pa-keeper", "change_group", "view_contract")
    target = _entity_group(tenant, "Nurse")
    target.permissions.set(_perms("view_contract_salary"))

    response = _set(client, target, *_perms("view_contract_salary", "view_contract"))

    assert response.status_code == 200, response.json()
    assert _codenames(target) == {"view_contract_salary", "view_contract"}


def test_group_of_another_entity_is_not_found(bootstrap_tenant):
    mine = bootstrap_tenant("pa-other-a")
    theirs = bootstrap_tenant("pa-other-b")
    client = _actor(mine, "pa-outsider", "change_group", "view_contract")
    their_group = _entity_group(theirs, "Their Nurse")

    response = _set(client, their_group, *_perms("view_contract"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "group_not_in_entity"
    assert _codenames(their_group) == set()


def test_group_shared_with_another_entity_needs_platform_permission(bootstrap_tenant):
    mine = bootstrap_tenant("pa-shared-a")
    theirs = bootstrap_tenant("pa-shared-b")
    client = _actor(mine, "pa-sharer", "change_group", "view_contract")
    shared = _entity_group(mine, "Shared Admin")
    EntityGroup.objects.create(entity=theirs["entity"], group=shared, state="Active")

    response = _set(client, shared, *_perms("view_contract"))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "group_shared"
    assert _codenames(shared) == set()


def test_entity_type_template_group_needs_platform_permission(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-template")
    client = _actor(tenant, "pa-templater", "change_group", "view_contract")
    template = _entity_group(tenant, "Template Nurse")
    EntityTypeGroup.objects.create(entity_type=tenant["entity"].entity_type, group=template)

    response = _set(client, template, *_perms("view_contract"))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "group_shared"


def test_platform_level_actor_can_change_a_shared_group(bootstrap_tenant):
    mine = bootstrap_tenant("pa-platform-a")
    theirs = bootstrap_tenant("pa-platform-b")
    client = _actor(mine, "pa-platform", "change_group", "change_entitytype", "view_contract")
    shared = _entity_group(mine, "Shared Clerk")
    EntityGroup.objects.create(entity=theirs["entity"], group=shared, state="Active")

    response = _set(client, shared, *_perms("view_contract"))

    assert response.status_code == 200, response.json()
    assert _codenames(shared) == {"view_contract"}


def test_non_editable_group_of_the_entity_needs_platform_permission(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-not-editable")
    client = _actor(tenant, "pa-ne-actor", "change_group", "view_contract")
    fixed = _entity_group(tenant, "Fixed Profile", editable=False)

    response = _set(client, fixed, *_perms("view_contract"))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "group_not_editable"
    assert _codenames(fixed) == set()


def test_platform_level_actor_can_change_a_non_editable_group(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-ne-platform")
    client = _actor(tenant, "pa-ne-platform-actor", "change_group", "change_entitytype", "view_contract")
    fixed = _entity_group(tenant, "Fixed Clerk", editable=False)

    response = _set(client, fixed, *_perms("view_contract"))

    assert response.status_code == 200, response.json()


def test_a_group_created_by_the_entity_is_editable(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-create-group")

    response = tenant["client"].post(
        f"/api/django_resaas/entitys/{tenant['entity'].id}/createGroup/", {"name": "Own Nurse"}, format="json"
    )

    assert response.status_code == 200, response.content
    assert Group.objects.get(name="Own Nurse").editable is True


def test_editable_cannot_be_set_by_the_client(bootstrap_tenant):
    tenant = bootstrap_tenant("pa-editable-ro")
    tenant["client"].raise_request_exception = False

    tenant["client"].post("/api/auth/groups/", {"name": "Sneaky", "editable": True}, format="json")

    group = Group.objects.filter(name="Sneaky").first()
    assert group is None or group.editable is False
