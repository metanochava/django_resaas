"""GroupAPIView (auth/groups/): every action needs its permission; a caller
sees the current Entity's groups and changes only an editable, unshared one
of that Entity - unless they are platform level (change_entitytype, Root).
See core/services/group_access_service.py."""
import pytest
from django.contrib.auth.models import Permission

from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.group import Group
from django_resaas.saas.tests.test_permission_api_security import _actor, _entity_group, _perms

pytestmark = pytest.mark.django_db

URL = "/api/auth/groups/"


def _names(response):
    data = response.json()
    rows = data["results"] if isinstance(data, dict) and "results" in data else data
    return {row["name"] for row in rows}


# ------------------------------------------------------------------ permissions per action

@pytest.mark.parametrize("method,suffix,body", [
    ("get", "", None),
    ("post", "", {"name": "New"}),
])
def test_collection_actions_need_their_permission(bootstrap_tenant, method, suffix, body):
    tenant = bootstrap_tenant(f"ga-coll-{method}")
    client = _actor(tenant, f"ga-coll-{method}-actor")

    response = getattr(client, method)(URL + suffix, body, format="json")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


@pytest.mark.parametrize("method,suffix,body", [
    ("get", "", None),
    ("get", "permissions/", None),
    ("put", "", {"name": "Renamed"}),
    ("delete", "", None),
    ("post", "addPermission/", {"codename": "x_custom", "name": "X"}),
    ("post", "removePermission/", {"codename": "view_contract"}),
])
def test_detail_actions_need_their_permission(bootstrap_tenant, method, suffix, body):
    tenant = bootstrap_tenant(f"ga-det-{method}-{suffix.strip('/').lower() or 'x'}")
    client = _actor(tenant, f"ga-det-{method}-{suffix.strip('/').lower() or 'x'}-actor")
    target = _entity_group(tenant, "Nurse")
    target.permissions.set(_perms("view_contract"))

    response = getattr(client, method)(f"{URL}{target.id}/{suffix}", body, format="json")

    assert response.status_code == 403
    assert Group.objects.filter(id=target.id, name="Nurse").exists()
    assert set(target.permissions.values_list("codename", flat=True)) == {"view_contract"}


# ------------------------------------------------------------------ visibility

def test_list_shows_only_the_current_entitys_groups(bootstrap_tenant):
    mine = bootstrap_tenant("ga-list-a")
    theirs = bootstrap_tenant("ga-list-b")
    client = _actor(mine, "ga-lister", "list_group")
    _entity_group(mine, "My Nurse")
    _entity_group(theirs, "Their Nurse")

    names = _names(client.get(URL, {"page_size": 0}))

    assert "My Nurse" in names
    assert "Their Nurse" not in names
    assert "Root" not in names


def test_platform_level_lists_every_group(bootstrap_tenant):
    mine = bootstrap_tenant("ga-plat-list-a")
    theirs = bootstrap_tenant("ga-plat-list-b")
    client = _actor(mine, "ga-plat-lister", "list_group", "change_entitytype")
    _entity_group(theirs, "Their Clerk")

    assert "Their Clerk" in _names(client.get(URL, {"page_size": 0}))


def test_a_group_of_another_entity_is_not_found(bootstrap_tenant):
    mine = bootstrap_tenant("ga-404-a")
    theirs = bootstrap_tenant("ga-404-b")
    client = _actor(mine, "ga-404-actor", "view_group", "change_group", "delete_group")
    their_group = _entity_group(theirs, "Their Admin")

    for response in (
        client.get(f"{URL}{their_group.id}/"),
        client.get(f"{URL}{their_group.id}/permissions/"),
        client.put(f"{URL}{their_group.id}/", {"name": "Hijacked"}, format="json"),
        client.delete(f"{URL}{their_group.id}/"),
    ):
        assert response.status_code == 404

    assert Group.objects.filter(id=their_group.id, name="Their Admin").exists()


# ------------------------------------------------------------------ create

def test_an_entity_creates_an_editable_group_linked_to_itself(bootstrap_tenant):
    tenant = bootstrap_tenant("ga-create")
    client = _actor(tenant, "ga-creator", "add_group")

    response = client.post(URL, {"name": "Own Clerk", "editable": False}, format="json")

    assert response.status_code == 201, response.json()
    group = Group.objects.get(name="Own Clerk")
    assert group.editable is True
    assert EntityGroup.objects.filter(group=group, entity=tenant["entity"]).exists()


# ------------------------------------------------------------------ change / delete

def test_editable_group_of_the_entity_can_be_renamed_and_deleted(bootstrap_tenant):
    tenant = bootstrap_tenant("ga-edit-ok")
    client = _actor(tenant, "ga-editor", "change_group", "delete_group")
    target = _entity_group(tenant, "Nurse")

    renamed = client.put(f"{URL}{target.id}/", {"name": "Senior Nurse"}, format="json")
    deleted = client.delete(f"{URL}{target.id}/")

    assert renamed.status_code == 202
    assert deleted.status_code == 202
    assert not Group.objects.filter(id=target.id).exists()


@pytest.mark.parametrize("kind,code", [("not_editable", "group_not_editable"), ("shared", "group_shared")])
def test_non_editable_or_shared_groups_are_platform_only(bootstrap_tenant, kind, code):
    mine = bootstrap_tenant(f"ga-{kind}-a")
    theirs = bootstrap_tenant(f"ga-{kind}-b")
    client = _actor(mine, f"ga-{kind}-actor", "change_group", "delete_group")
    target = _entity_group(mine, "Admin-like", editable=(kind != "not_editable"))
    if kind == "shared":
        EntityGroup.objects.create(entity=theirs["entity"], group=target, state="Active")

    renamed = client.put(f"{URL}{target.id}/", {"name": "Hijacked"}, format="json")
    deleted = client.delete(f"{URL}{target.id}/")

    for response in (renamed, deleted):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == code
    assert Group.objects.filter(id=target.id, name="Admin-like").exists()


def test_cannot_delete_the_active_group(bootstrap_tenant):
    tenant = bootstrap_tenant("ga-self-delete")
    client = _actor(tenant, "ga-self-deleter", "delete_group")
    own = Group.objects.get(name="ga-self-deleter-group")

    response = client.delete(f"{URL}{own.id}/")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "cannot_delete_active_group"
    assert Group.objects.filter(id=own.id).exists()


# ------------------------------------------------------------------ addPermission / removePermission

def test_add_permission_cannot_reuse_a_real_codename(bootstrap_tenant):
    """check_permission matches codenames only: a 'custom' permission named
    view_contract_salary would grant the real capability."""
    tenant = bootstrap_tenant("ga-codename")
    client = _actor(tenant, "ga-codename-actor", "change_group", "add_permission")
    target = _entity_group(tenant, "Nurse")

    response = client.post(
        f"{URL}{target.id}/addPermission/", {"codename": "view_contract_salary", "name": "x"}, format="json"
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "permission_codename_exists"
    assert not target.permissions.exists()


def test_add_permission_to_own_group_cannot_escalate(bootstrap_tenant):
    tenant = bootstrap_tenant("ga-own-escalate")
    client = _actor(tenant, "ga-own-actor", "change_group", "add_permission")
    own = Group.objects.get(name="ga-own-actor-group")

    response = client.post(
        f"{URL}{own.id}/addPermission/", {"codename": "delete_group", "name": "x"}, format="json"
    )

    assert response.status_code == 409
    assert not own.permissions.filter(codename="delete_group").exists()


def test_new_custom_permission_needs_add_permission(bootstrap_tenant):
    tenant = bootstrap_tenant("ga-custom")
    target_codename = "approve_overtime_custom"

    denied_client = _actor(tenant, "ga-custom-denied", "change_group")
    target = _entity_group(tenant, "Nurse")
    denied = denied_client.post(
        f"{URL}{target.id}/addPermission/", {"codename": target_codename, "name": "Approve overtime"}, format="json"
    )
    assert denied.status_code == 403
    assert not Permission.objects.filter(codename=target_codename).exists()

    allowed_client = _actor(tenant, "ga-custom-allowed", "change_group", "add_permission")
    allowed = allowed_client.post(
        f"{URL}{target.id}/addPermission/", {"codename": target_codename, "name": "Approve overtime"}, format="json"
    )
    assert allowed.status_code == 201, allowed.json()
    assert target.permissions.filter(codename=target_codename).exists()


def test_remove_permission_needs_the_permission_to_be_held(bootstrap_tenant):
    tenant = bootstrap_tenant("ga-remove")
    target = _entity_group(tenant, "Nurse")
    target.permissions.set(_perms("view_contract_salary", "view_contract"))

    denied = _actor(tenant, "ga-remove-denied", "change_group").post(
        f"{URL}{target.id}/removePermission/", {"codename": "view_contract_salary"}, format="json"
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "permission_not_held"

    allowed = _actor(tenant, "ga-remove-allowed", "change_group", "view_contract").post(
        f"{URL}{target.id}/removePermission/", {"codename": "view_contract"}, format="json"
    )
    assert allowed.status_code == 200, allowed.json()
    assert set(target.permissions.values_list("codename", flat=True)) == {"view_contract_salary"}
