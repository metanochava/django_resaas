"""Menu Manager API (phase 13): platform administration, fail closed.

Root manages the menus; a profile without the menu permissions gets 403 on
every action; a profile with only view_menu can read but not write; the
read-only actions (validate, resources) change nothing; framework menus are not
deleted; an item's parent must belong to the same menu.
"""
import pytest

from django_resaas.saas.models.menu import Menu, MenuItem
from django_resaas.saas.tests.test_permission_api_security import _actor

pytestmark = pytest.mark.django_db

MENUS = "/api/django_resaas/menus/"
ITEMS = "/api/django_resaas/menuitems/"


def _denied(response):
    assert response.status_code == 403, response.status_code
    assert response.json()["error"]["code"] == "permission_denied"


@pytest.mark.parametrize("method,url,body", [
    ("get", MENUS, None),
    ("post", MENUS, {"code": "x", "name": "x", "label": "X"}),
    ("get", MENUS + "validate/", None),
    ("get", MENUS + "resources/", None),
    ("get", ITEMS, None),
    ("post", ITEMS, {"menu": "", "label": "x", "item_type": "page", "route_name": "x"}),
])
def test_profile_without_menu_permissions_is_denied(bootstrap_tenant, method, url, body):
    tenant = bootstrap_tenant(f"menu-api-denied-{method}-{abs(hash(url))}")
    client = _actor(tenant, f"menu-api-denied-{method}-{abs(hash(url))}-actor")

    _denied(getattr(client, method)(url, body, format="json"))
    assert not Menu.objects.filter(code="x").exists()


def test_view_only_profile_reads_but_cannot_write(bootstrap_tenant):
    tenant = bootstrap_tenant("menu-api-view-only")
    client = _actor(tenant, "menu-api-view-only-actor", "list_menu", "view_menu")

    assert client.get(MENUS).status_code == 200
    _denied(client.post(MENUS, {"code": "blocked", "name": "blocked", "label": "Blocked"}, format="json"))
    assert not Menu.objects.filter(code="blocked").exists()


def test_root_creates_a_menu_and_an_item(bootstrap_tenant):
    tenant = bootstrap_tenant("menu-api-root")
    client = tenant["client"]

    created = client.post(MENUS, {"code": "ops", "name": "ops", "label": "Operations"}, format="json")
    assert created.status_code == 201, created.content
    menu_id = created.json()["id"]

    item = client.post(ITEMS, {"menu": menu_id, "label": "Reports", "item_type": "page",
                               "route_name": "reports", "permission_code": "view_report"}, format="json")

    assert item.status_code == 201, item.content
    assert MenuItem.objects.filter(menu_id=menu_id, route_name="reports").exists()


def test_validate_reports_problems_and_changes_nothing(bootstrap_tenant):
    tenant = bootstrap_tenant("menu-api-validate")
    client = tenant["client"]
    menu = Menu.objects.create(code="empty-api", name="e", label="E")
    before = MenuItem.objects.count()

    response = client.get(MENUS + "validate/")

    assert response.status_code == 200
    assert any(issue["code"] == "empty_menu" and issue["menu_code"] == "empty-api" for issue in response.json())
    assert MenuItem.objects.count() == before
    assert Menu.objects.filter(id=menu.id).exists()


def test_resources_lists_the_declared_crud_models(bootstrap_tenant):
    tenant = bootstrap_tenant("menu-api-resources")

    response = tenant["client"].get(MENUS + "resources/")

    assert response.status_code == 200
    assert "django_resaas.branch" in {row["key"] for row in response.json()}


def test_framework_menu_cannot_be_deleted(bootstrap_tenant):
    tenant = bootstrap_tenant("menu-api-system")
    system = Menu.objects.create(code="system-api", name="s", label="S", is_system=True)

    response = tenant["client"].delete(f"{MENUS}{system.id}/")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "system_menu"
    assert Menu.objects.filter(id=system.id).exists()


def test_item_parent_must_belong_to_the_same_menu(bootstrap_tenant):
    tenant = bootstrap_tenant("menu-api-parent")
    client = tenant["client"]
    first = Menu.objects.create(code="first-api", name="f", label="F")
    second = Menu.objects.create(code="second-api", name="s", label="S")
    parent = MenuItem.objects.create(menu=first, label="g", item_type=MenuItem.GROUP)

    response = client.post(ITEMS, {"menu": second.id, "parent": str(parent.id), "label": "x",
                                   "item_type": "page", "route_name": "x"}, format="json")

    assert response.status_code == 400
    assert "parent" in response.json()["error"]["details"]
