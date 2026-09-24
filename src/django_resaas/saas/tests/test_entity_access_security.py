"""EntityAPIView / EntityTypeAPIView per-action authorization
(ActionPermissionMixin) and the deploy endpoints.

Membership reads (the caller's own Entities, their branding) need no
permission - the login / context selection runs before any profile. Every
other action needs its permission in the signed context and, for an Entity,
works on the context's Entity only (unless platform level)."""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity_type_group import EntityTypeGroup
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.group import Group
from django_resaas.saas.models.user import User
from django_resaas.saas.tests.test_permission_api_security import _actor

pytestmark = pytest.mark.django_db

ENTITY = "/api/django_resaas/entitys/"
TYPES = "/api/django_resaas/entitytypes/"


# ------------------------------------------------------------------ EntityAPIView

def test_a_member_without_permissions_reads_but_cannot_change_their_entity(bootstrap_tenant):
    tenant = bootstrap_tenant("ea-member")
    client = _actor(tenant, "ea-member-actor")
    url = f"{ENTITY}{tenant['entity'].id}/"

    assert client.get(ENTITY).status_code == 200
    assert client.get(url).status_code == 200
    assert client.get(f"{url}themeGet/").status_code == 200

    for response in (
        client.patch(url, {"name": "Hijacked"}, format="json"),
        client.post(f"{url}addUser/", {"user": str(tenant["user"].id)}, format="json"),
        client.post(f"{url}createGroup/", {"name": "Mine"}, format="json"),
        client.get(f"{url}users/"),
    ):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "permission_denied"

    tenant["entity"].refresh_from_db()
    assert tenant["entity"].name != "Hijacked"


def test_permissions_apply_to_the_context_entity_only(bootstrap_tenant):
    mine = bootstrap_tenant("ea-ctx-a")
    theirs = bootstrap_tenant("ea-ctx-b")
    client = _actor(mine, "ea-ctx-actor", "change_entity", "view_entity")
    # the actor is also a plain member of the other Entity
    EntityUser.objects.get_or_create(user=User.objects.get(username="ea-ctx-actor"), entity=theirs["entity"])

    own = client.patch(f"{ENTITY}{mine['entity'].id}/", {"name": "Renamed A"}, format="json")
    other = client.patch(f"{ENTITY}{theirs['entity'].id}/", {"name": "Hijacked B"}, format="json")
    other_users = client.get(f"{ENTITY}{theirs['entity'].id}/users/")

    assert own.status_code == 200, own.json()
    assert other.status_code == 404
    assert other_users.status_code == 404
    theirs["entity"].refresh_from_db()
    assert theirs["entity"].name != "Hijacked B"


def test_qr_of_another_entity_is_not_found(bootstrap_tenant):
    mine = bootstrap_tenant("ea-qr-a")
    theirs = bootstrap_tenant("ea-qr-b")
    client = _actor(mine, "ea-qr-actor", "view_entity")

    assert client.get(f"{ENTITY}{theirs['entity'].id}/qr/").status_code == 404


def test_an_entity_can_only_link_its_entity_types_template_groups(bootstrap_tenant):
    """Linking Root to an Entity would let its admins hand Root out."""
    tenant = bootstrap_tenant("ea-link")
    client = _actor(tenant, "ea-link-actor", "add_entitygroup")
    template = Group.objects.create(name="Template Nurse")
    EntityTypeGroup.objects.create(entity_type=tenant["entity"].entity_type, group=template)
    url = f"{ENTITY}{tenant['entity'].id}/addGroup/"

    root = client.post(url, {"group": str(tenant["root_group"].id)}, format="json")
    ok = client.post(url, {"group": str(template.id)}, format="json")

    assert root.status_code == 403
    assert root.json()["error"]["code"] == "group_not_in_entity_type"
    assert not EntityGroup.objects.filter(entity=tenant["entity"], group=tenant["root_group"]).exists()
    assert ok.status_code == 200
    assert EntityGroup.objects.filter(entity=tenant["entity"], group=template).exists()


def test_platform_level_keeps_full_access(bootstrap_tenant):
    tenant = bootstrap_tenant("ea-platform")

    response = tenant["client"].get(f"{ENTITY}{tenant['entity'].id}/groups/")

    assert response.status_code == 200


# ------------------------------------------------------------------ EntityTypeAPIView

def test_a_member_reads_their_own_entity_type_only(bootstrap_tenant):
    mine = bootstrap_tenant("et-own-a")
    client = _actor(mine, "et-own-actor")
    own_type = mine["entity"].entity_type_id
    # bootstrap_tenant always uses the same EntityType: make a real other one
    other_type = EntityType.objects.create(name="Other Type", state="Active").id

    assert client.get(f"{TYPES}{own_type}/permissions/").status_code == 200
    assert client.get(f"{TYPES}{own_type}/groups/").status_code == 200
    assert client.get(f"{TYPES}{other_type}/permissions/").status_code == 403
    # every Entity / Branch of a type crosses tenants
    assert client.get(f"{TYPES}{own_type}/entitys/").status_code == 403
    assert client.get(f"{TYPES}{own_type}/branches_map/").status_code == 403


def test_entity_type_writes_are_platform_level(bootstrap_tenant):
    tenant = bootstrap_tenant("et-write")
    client = _actor(tenant, "et-write-actor", "change_entity", "add_group")
    own_type = tenant["entity"].entity_type_id

    for response in (
        client.post(f"{TYPES}{own_type}/createGroup/", {"name": "X"}, format="json"),
        client.post(f"{TYPES}{own_type}/addGroup/", {"group": str(tenant["root_group"].id)}, format="json"),
        client.patch(f"{TYPES}{own_type}/", {"name": "Hijacked"}, format="json"),
    ):
        assert response.status_code == 403


def test_entity_type_branding_stays_public(bootstrap_tenant):
    tenant = bootstrap_tenant("et-public")

    response = APIClient().get(f"{TYPES}{tenant['entity'].entity_type_id}/themeGet/")

    assert response.status_code == 200


# ------------------------------------------------------------------ deploy

@override_settings(DEPLOY_TOKEN="test-deploy-token")
def test_rollback_needs_post_and_the_token(monkeypatch):
    from django_resaas import view

    monkeypatch.setattr(view, "DEPLOY_TOKEN", "test-deploy-token")
    client = APIClient()

    assert client.get("/api/deploy/rollback/", {"token": "test-deploy-token"}).status_code == 405
    assert client.post("/api/deploy/rollback/", {}, HTTP_X_DEPLOY_TOKEN="wrong").status_code == 403
    assert client.post("/api/deploy/github/", {}, format="json").status_code == 403


def test_deploy_refuses_everything_without_a_configured_token(monkeypatch):
    from django_resaas import view

    monkeypatch.setattr(view, "DEPLOY_TOKEN", None)
    client = APIClient()

    # the old hard-coded fallback is not a password any more
    assert client.post("/api/deploy/github/?token=@SaaS@", {"tag": "x"}, format="json").status_code == 403
    assert client.get("/api/deploy/status/", {"token": "@SaaS@"}).status_code == 403
