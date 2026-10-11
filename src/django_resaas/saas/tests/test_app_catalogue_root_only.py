"""The App catalogue (the list_app page: AppAPIView apps/ and AppSchemaAPIView
resaasapps/) is platform administration: every action needs its permission
(fail closed) and only the Root profile holds those permissions -
saas/profiles.py revokes APP_PERMISSIONS from the Admin group.
resaasapps/<app>/<model>/schema/ stays open to any authenticated caller: every
generic form loads its schema from it."""
import pytest

from django_resaas.saas.core.utils.group_creator import group_creator
from django_resaas.saas.models.app import App
from django_resaas.saas.models.group import Group
from django_resaas.saas.profiles import APP_PERMISSIONS, CORE_PROFILES, PLATFORM_PERMISSIONS
from django_resaas.saas.tests.test_permission_api_security import _actor, _perms

pytestmark = pytest.mark.django_db

APPS = "/api/django_resaas/apps/"
SCHEMA = "/api/django_resaas/resaasapps/"


def _denied(response):
    assert response.status_code == 403, response.status_code
    assert response.json()["error"]["code"] == "permission_denied"


# ------------------------------------------------------------------ apps/

@pytest.mark.parametrize("method,suffix,body", [
    ("get", "", None),
    ("post", "", {"name": "billing"}),
])
def test_app_collection_actions_need_their_permission(bootstrap_tenant, method, suffix, body):
    tenant = bootstrap_tenant(f"appcat-coll-{method}")
    client = _actor(tenant, f"appcat-coll-{method}-actor")

    _denied(getattr(client, method)(APPS + suffix, body, format="json"))
    assert not App.objects.filter(name="billing").exists()


@pytest.mark.parametrize("method,suffix,body", [
    ("get", "", None),
    ("patch", "", {"state": "Inactive"}),
    ("delete", "", None),
    ("get", "entityTypes/", None),
    ("post", "addEntityType/", {"id": "x"}),
    ("post", "removeEntityType/", {"id": "x"}),
])
def test_app_detail_actions_need_their_permission(bootstrap_tenant, method, suffix, body):
    slug = suffix.strip("/").lower() or "x"
    tenant = bootstrap_tenant(f"appcat-det-{method}-{slug}")
    client = _actor(tenant, f"appcat-det-{method}-{slug}-actor")
    app = App.objects.create(name="billing")

    _denied(getattr(client, method)(f"{APPS}{app.id}/{suffix}", body, format="json"))
    assert App.objects.filter(id=app.id).exists()


def test_list_app_alone_lists_but_cannot_change(bootstrap_tenant):
    tenant = bootstrap_tenant("appcat-list-only")
    client = _actor(tenant, "appcat-list-only-actor", "list_app")
    app = App.objects.create(name="billing")

    assert client.get(APPS, {"page_size": 0}).status_code == 200
    _denied(client.patch(f"{APPS}{app.id}/", {"state": "Inactive"}, format="json"))


def test_root_manages_the_catalogue(bootstrap_tenant):
    tenant = bootstrap_tenant("appcat-root")
    app = App.objects.create(name="billing")

    assert tenant["client"].get(APPS, {"page_size": 0}).status_code == 200
    assert tenant["client"].get(f"{APPS}{app.id}/entityTypes/").status_code == 200


# ------------------------------------------------------------------ resaasapps/

@pytest.mark.parametrize("method,path,body", [
    ("get", "", None),
    ("post", "", {"name": "billing"}),
    ("get", "lookup/?app=django_resaas", None),
    ("get", "django_resaas/", None),
    ("delete", "billing/", None),
])
def test_module_actions_need_their_permission(bootstrap_tenant, method, path, body):
    slug = path.split("/")[0].split("?")[0] or "root"
    tenant = bootstrap_tenant(f"appcat-mod-{method}-{slug}")
    client = _actor(tenant, f"appcat-mod-{method}-{slug}-actor")

    _denied(getattr(client, method)(SCHEMA + path, body, format="json"))


def test_model_schema_stays_open_to_authenticated_callers(bootstrap_tenant):
    tenant = bootstrap_tenant("appcat-schema")
    client = _actor(tenant, "appcat-schema-actor")

    response = client.get(f"{SCHEMA}django_resaas/App/schema/")

    assert response.status_code == 200


# ------------------------------------------------------------------ profiles

def test_only_root_keeps_the_app_permissions(bootstrap_tenant):
    bootstrap_tenant("appcat-profiles")
    admin = Group.objects.get_or_create(name="Admin")[0]
    admin.permissions.add(*_perms(*APP_PERMISSIONS))

    group_creator(CORE_PROFILES)

    held = set(admin.permissions.values_list("codename", flat=True))
    assert not held & set(APP_PERMISSIONS), held & set(APP_PERMISSIONS)

    root = set(Group.objects.get(name="Root").permissions.values_list("codename", flat=True))
    assert {"list_app", "view_app", "add_app", "change_app", "delete_app"} <= root


def test_admin_loses_every_lib_permission_and_is_not_platform_level(bootstrap_tenant):
    """Root = the lib/platform (Apps, EntityTypes, scaffold, IDE); Admin manages
    its own Entity only - without change_entitytype it is not platform level, so
    group_access_service limits it to the editable profiles of its Entity."""
    bootstrap_tenant("platform-admin")
    admin = Group.objects.get_or_create(name="Admin")[0]
    admin.permissions.add(*_perms(*PLATFORM_PERMISSIONS, "change_group", "add_branch"))

    group_creator(CORE_PROFILES)

    held = set(admin.permissions.values_list("codename", flat=True))
    assert not held & set(PLATFORM_PERMISSIONS), sorted(held & set(PLATFORM_PERMISSIONS))
    assert "change_entitytype" not in held
    # Entity administration stays
    assert {"change_group", "add_branch"} <= held

    root = set(Group.objects.get(name="Root").permissions.values_list("codename", flat=True))
    assert {"change_entitytype", "view_scaffold", "change_scaffold", "list_app"} <= root

