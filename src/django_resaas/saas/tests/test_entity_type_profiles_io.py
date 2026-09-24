"""EntityType -> profiles -> permissions: JSON / PDF export and JSON import
(entitytypes/{id}/profiles_json|profiles_pdf|import_profiles)."""
import json

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile

from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity_type_group import EntityTypeGroup
from django_resaas.saas.models.group import Group
from django_resaas.saas.tests.test_permission_api_security import _actor

pytestmark = pytest.mark.django_db

URL = "/api/django_resaas/entitytypes/"
PLATFORM = ("view_entitytype", "change_entitytype", "change_group", "view_group", "view_permission",
            "view_entity")


def _template(tenant, name, *perms):
    group = Group.objects.create(name=name)
    group.permissions.set(Permission.objects.filter(codename__in=perms, content_type__app_label__in=("django_resaas", "auth")))
    EntityTypeGroup.objects.create(entity_type=tenant["entity"].entity_type, group=group)
    return group


def _upload(client, entity_type_id, payload, mode=None, raw=None):
    body = raw if raw is not None else json.dumps(payload).encode()
    data = {"file": SimpleUploadedFile("profiles.json", body, content_type="application/json")}
    if mode:
        data["mode"] = mode
    return client.post(f"{URL}{entity_type_id}/import_profiles/", data, format="multipart")


def _codenames(group):
    return set(group.permissions.values_list("codename", flat=True))


def _profiles(*profiles):
    return {"format": "resaas.entity_type_profiles", "version": 1, "profiles": list(profiles)}


# ------------------------------------------------------------------ export

def test_json_exports_profiles_and_their_permissions(bootstrap_tenant):
    tenant = bootstrap_tenant("etp-export")
    _template(tenant, "Template Nurse", "view_group")
    client = _actor(tenant, "etp-export-actor", *PLATFORM)

    response = client.get(f"{URL}{tenant['entity'].entity_type_id}/profiles_json/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    data = json.loads(response.content)
    assert data["format"] == "resaas.entity_type_profiles" and data["version"] == 1
    nurse = next(p for p in data["profiles"] if p["name"] == "Template Nurse")
    assert {p["codename"] for p in nurse["permissions"]} == {"view_group"}
    assert set(nurse["permissions"][0]) == {"app", "model", "codename", "name"}


def test_pdf_is_generated(bootstrap_tenant):
    tenant = bootstrap_tenant("etp-pdf")
    _template(tenant, "Template Clerk", "view_group")
    client = _actor(tenant, "etp-pdf-actor", *PLATFORM)

    response = client.get(f"{URL}{tenant['entity'].entity_type_id}/profiles_pdf/")

    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"


def test_a_member_reads_only_its_own_entity_types_profiles(bootstrap_tenant):
    tenant = bootstrap_tenant("etp-member")
    client = _actor(tenant, "etp-member-actor")
    other = EntityType.objects.create(name="Other Type", state="Active")

    assert client.get(f"{URL}{tenant['entity'].entity_type_id}/profiles_json/").status_code == 200
    assert client.get(f"{URL}{other.id}/profiles_json/").status_code == 403


# ------------------------------------------------------------------ import

def test_import_is_platform_level(bootstrap_tenant):
    tenant = bootstrap_tenant("etp-denied")
    client = _actor(tenant, "etp-denied-actor", "change_group", "view_group")

    response = _upload(client, tenant["entity"].entity_type_id, _profiles({"name": "X", "permissions": []}))

    assert response.status_code == 403
    assert not Group.objects.filter(name="X").exists()


def test_import_creates_and_links_profiles_and_adds_permissions(bootstrap_tenant):
    tenant = bootstrap_tenant("etp-add")
    existing = _template(tenant, "Template Doctor", "view_group")
    client = _actor(tenant, "etp-add-actor", *PLATFORM)
    type_id = tenant["entity"].entity_type_id

    response = _upload(client, type_id, _profiles(
        {"name": "Template Doctor", "permissions": [{"app": "auth", "codename": "view_permission"}]},
        {"name": "Clinic Porter", "permissions": ["view_entity"]},
    ))

    assert response.status_code == 200, response.json()
    assert response.json()["created"] == 1
    assert _codenames(existing) == {"view_group", "view_permission"}
    porter = Group.objects.get(name="Clinic Porter")
    assert _codenames(porter) == {"view_entity"}
    assert EntityTypeGroup.objects.filter(entity_type_id=type_id, group=porter).exists()


def test_replace_only_touches_the_profiles_in_the_file(bootstrap_tenant):
    tenant = bootstrap_tenant("etp-replace")
    listed = _template(tenant, "Listed", "view_group", "view_entity")
    untouched = _template(tenant, "Untouched", "view_group")
    client = _actor(tenant, "etp-replace-actor", *PLATFORM)

    response = _upload(client, tenant["entity"].entity_type_id,
                       _profiles({"name": "Listed", "permissions": ["view_entity"]}), mode="replace")

    assert response.status_code == 200, response.json()
    assert _codenames(listed) == {"view_entity"}
    assert _codenames(untouched) == {"view_group"}


def test_an_invalid_profile_changes_nothing(bootstrap_tenant):
    tenant = bootstrap_tenant("etp-invalid")
    client = _actor(tenant, "etp-invalid-actor", *PLATFORM)

    response = _upload(client, tenant["entity"].entity_type_id, _profiles(
        {"name": "Good", "permissions": ["view_entity"]},
        {"name": "Bad", "permissions": ["does_not_exist"]},
    ))

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_profiles"
    assert list(error["details"]["profiles"]) == ["profiles[1] Bad"]
    assert not Group.objects.filter(name__in=["Good", "Bad"]).exists()


def test_platform_profiles_and_permissions_are_refused(bootstrap_tenant):
    """A template is inherited by every Entity of the type."""
    tenant = bootstrap_tenant("etp-platform")
    client = _actor(tenant, "etp-platform-actor", *PLATFORM)
    type_id = tenant["entity"].entity_type_id

    root = _upload(client, type_id, _profiles({"name": "Root", "permissions": []}))
    grant = _upload(client, type_id, _profiles({"name": "Sneaky", "permissions": ["change_entitytype"]}))

    for response in (root, grant):
        assert response.status_code == 400
    assert not EntityTypeGroup.objects.filter(entity_type_id=type_id, group__name="Root").exists()
    assert not Group.objects.filter(name="Sneaky").exists()


def test_bad_files_are_rejected(bootstrap_tenant):
    tenant = bootstrap_tenant("etp-bad")
    client = _actor(tenant, "etp-bad-actor", *PLATFORM)
    type_id = tenant["entity"].entity_type_id

    assert _upload(client, type_id, None, raw=b"{not json").json()["error"]["code"] == "invalid_json"
    assert _upload(client, type_id, {"x": 1}).json()["error"]["code"] == "profiles_missing"
    duplicated = _upload(client, type_id, _profiles({"name": "A", "permissions": []}, {"name": "a", "permissions": []}))
    assert duplicated.json()["error"]["code"] == "invalid_profiles"
    assert _upload(client, type_id, _profiles(), mode="merge").json()["error"]["code"] == "invalid_mode"


def test_import_cannot_grant_what_the_caller_does_not_hold(bootstrap_tenant):
    tenant = bootstrap_tenant("etp-escalate")
    client = _actor(tenant, "etp-esc-actor", "change_entitytype", "view_entitytype")

    response = _upload(client, tenant["entity"].entity_type_id,
                       _profiles({"name": "New One", "permissions": [{"app": "django_resaas", "codename": "delete_group"}]}))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_not_held"
    assert not Group.objects.filter(name="New One").exists()


def test_exported_file_imports_back_unchanged(bootstrap_tenant):
    tenant = bootstrap_tenant("etp-roundtrip")
    group = _template(tenant, "Round Trip", "view_group", "view_entity")
    client = _actor(tenant, "etp-rt-actor", *PLATFORM)
    type_id = tenant["entity"].entity_type_id
    exported = client.get(f"{URL}{type_id}/profiles_json/").content

    response = _upload(client, type_id, None, raw=exported, mode="replace")

    assert response.status_code == 200, response.json()
    mine = next(p for p in response.json()["profiles"] if p["name"] == "Round Trip")
    assert (mine["added"], mine["removed"]) == (0, 0)
    assert _codenames(group) == {"view_group", "view_entity"}
