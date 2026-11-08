"""UserAPIView.menus() - a sidebar may declare a direct top-level link
({"MENU", "ICON", "ROUTE", "ROLE"}, no SUBMENUS): shown only with its
permission, never without ROLE (fail closed)."""
import importlib
import types

import pytest

pytestmark = pytest.mark.django_db


def _fake_sidebar(role):
    return types.SimpleNamespace(ALL=[
        {"MENU": "Patients", "ICON": "groups", "ROUTE": "list_paciente", "ROLE": role},
        {"MENU": "No role", "ICON": "x", "ROUTE": "anything"},
    ])


@pytest.fixture
def notifications_sidebar(monkeypatch):
    """Replaces the notifications module's sidebar (active by default)."""
    real = importlib.import_module
    holder = {}

    def fake(name, *args, **kwargs):
        if name.endswith("notifications.sidebar") and "module" in holder:
            return holder["module"]
        return real(name, *args, **kwargs)

    monkeypatch.setattr("django_resaas.saas.data.user.views.user.importlib.import_module", fake)
    return holder


def _menus(tenant):
    response = tenant["client"].get(f"/api/django_resaas/users/{tenant['user'].id}/menus/")
    assert response.status_code == 200, response.data
    return response.data


def test_direct_link_shown_with_its_permission(bootstrap_tenant, notifications_sidebar):
    tenant = bootstrap_tenant("menus-direct-ok")
    codename = tenant["root_group"].permissions.values_list("codename", flat=True).order_by("codename").first()
    assert codename
    notifications_sidebar["module"] = _fake_sidebar(codename)

    menus = _menus(tenant)

    link = next((m for m in menus if m["menu"] == "Patients"), None)
    assert link is not None, menus
    assert link["route"] == "list_paciente"
    assert link["submenu"] == []
    assert not any(m["menu"] == "No role" for m in menus)


def test_direct_link_hidden_without_the_permission(bootstrap_tenant, notifications_sidebar):
    tenant = bootstrap_tenant("menus-direct-no")
    notifications_sidebar["module"] = _fake_sidebar("permission_nobody_has")

    menus = _menus(tenant)

    assert not any(m["menu"] in ("Patients", "No role") for m in menus)


def test_direct_link_does_not_depend_on_its_modules_visibility(bootstrap_tenant, notifications_sidebar):
    """The module's eye hides its menu groups; a direct link follows only its
    own permission's eye (Group.hidden_menu_permissions)."""
    tenant = bootstrap_tenant("menus-direct-indep")
    group = tenant["root_group"]
    codename = group.permissions.values_list("codename", flat=True).order_by("codename").first()
    notifications_sidebar["module"] = types.SimpleNamespace(ALL=[
        {"MENU": "Patients", "ICON": "groups", "ROUTE": "list_paciente", "ROLE": codename},
        {"MENU": "Group", "ICON": "folder", "SUBMENUS": [
            {"menu": "Entry", "icon": "list", "route": "entry", "role": codename},
        ]},
    ])

    group.hidden_menu_apps = ["notifications"]
    group.save(update_fields=["hidden_menu_apps"])
    menus = [m["menu"] for m in _menus(tenant)]
    assert "Patients" in menus
    assert "Group" not in menus

    group.hidden_menu_permissions = [codename]
    group.save(update_fields=["hidden_menu_permissions"])
    assert "Patients" not in [m["menu"] for m in _menus(tenant)]

    group.hidden_menu_apps = []
    group.save(update_fields=["hidden_menu_apps"])
    # the module shown again: the hidden permission still hides its entries
    menus = _menus(tenant)
    assert "Patients" not in [m["menu"] for m in menus]
    assert "Group" not in [m["menu"] for m in menus]
