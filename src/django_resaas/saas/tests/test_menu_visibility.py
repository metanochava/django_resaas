"""A profile can hide a module from its menu (Permissions modal): the
group's hidden_menu_apps, set by POST groups/{id}/menu_visibility/ under the
rules for changing the group, and applied by UserAPIView.menus. The
permissions are unchanged."""
import pytest

from django_resaas.saas.models.group import Group

pytestmark = pytest.mark.django_db


def _menus(tenant):
    response = tenant["client"].get(f"/api/django_resaas/users/{tenant['user'].id}/menus/")
    assert response.status_code == 200, response.data
    return response.data


def _visibility(tenant, group, **body):
    return tenant["client"].post(
        f"/api/auth/groups/{group.id}/menu_visibility/", body, format="json"
    )


def test_hiding_a_module_removes_it_from_that_profiles_menu(bootstrap_tenant):
    tenant = bootstrap_tenant("menu-vis-hide")
    group = tenant["root_group"]
    assert any(m["app_label"] == "notifications" for m in _menus(tenant))
    perms_before = set(group.permissions.values_list("id", flat=True))

    response = _visibility(tenant, group, app_label="notifications", visible=False)

    # POST actions answer 200 or 202 (the API's write convention)
    assert response.status_code in (200, 202), response.data
    assert response.data["hidden_menu_apps"] == ["notifications"]
    assert not any(m["app_label"] == "notifications" for m in _menus(tenant))
    # only the menu: the permissions stay
    assert set(Group.objects.get(pk=group.pk).permissions.values_list("id", flat=True)) == perms_before


def test_showing_it_again(bootstrap_tenant):
    tenant = bootstrap_tenant("menu-vis-show")
    group = tenant["root_group"]
    _visibility(tenant, group, app_label="notifications", visible=False)

    response = _visibility(tenant, group, app_label="notifications", visible=True)

    assert response.status_code in (200, 202), response.data
    assert response.data["hidden_menu_apps"] == []
    assert any(m["app_label"] == "notifications" for m in _menus(tenant))


def test_unknown_module_and_bad_value_are_refused(bootstrap_tenant):
    tenant = bootstrap_tenant("menu-vis-bad")
    group = tenant["root_group"]

    assert _visibility(tenant, group, app_label="does_not_exist", visible=False).status_code == 400
    assert _visibility(tenant, group, app_label="notifications", visible="no").status_code == 400


def test_group_payload_carries_the_hidden_modules(bootstrap_tenant):
    tenant = bootstrap_tenant("menu-vis-payload")
    group = tenant["root_group"]
    _visibility(tenant, group, app_label="notifications", visible=False)

    response = tenant["client"].get(f"/api/auth/groups/{group.id}/")

    assert response.status_code == 200, response.data
    assert response.data["hidden_menu_apps"] == ["notifications"]
