"""MenuPermissionService (phase 7): visibility only, fail closed, no bypass."""
from types import SimpleNamespace

import pytest
from django.contrib.contenttypes.models import ContentType

from django_resaas.saas.core.services.menu_permission_service import MenuPermissionService
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.menu import MenuItem


def _item(**kwargs):
    defaults = dict(label="x", item_type=MenuItem.PAGE, route_name="x")
    defaults.update(kwargs)
    return MenuItem(**defaults)


class TestEffectivePermissions:

    def test_no_branch_or_group_means_no_permissions(self):
        request = SimpleNamespace(user=SimpleNamespace(id=1, is_superuser=True),
                                  branch_id=None, group_id=None)

        perms, hidden = MenuPermissionService.effective_permissions(request)

        assert perms == set()
        assert hidden == set()

    def test_superuser_gets_no_bypass_in_menus(self):
        request = SimpleNamespace(user=SimpleNamespace(id=1, is_superuser=True),
                                  branch_id=None, group_id=None)

        perms, _ = MenuPermissionService.effective_permissions(request)

        assert "view_branch" not in perms


class TestPageAndGroupVisibility:

    def test_page_with_permission_is_visible(self):
        item = _item(permission_code="view_branch")

        assert MenuPermissionService.can_see(item, {"view_branch"}) is True

    def test_page_without_permission_is_hidden(self):
        item = _item()

        assert MenuPermissionService.can_see(item, {"view_branch"}) is False

    def test_page_with_missing_permission_is_hidden(self):
        item = _item(permission_code="view_saude")

        assert MenuPermissionService.can_see(item, {"view_branch"}) is False

    def test_permission_comparison_ignores_case_and_spaces(self):
        item = _item(permission_code="  View_Branch ")

        assert MenuPermissionService.can_see(item, {"view_branch"}) is True

    def test_group_without_code_is_not_restricted_by_itself(self):
        group = _item(item_type=MenuItem.GROUP, route_name="")

        assert MenuPermissionService.can_see(group, set()) is True

    def test_group_with_code_needs_it(self):
        group = _item(item_type=MenuItem.GROUP, route_name="", permission_code="view_branch")

        assert MenuPermissionService.can_see(group, set()) is False
        assert MenuPermissionService.can_see(group, {"view_branch"}) is True


@pytest.mark.django_db
class TestResourceVisibility:

    def test_resource_without_code_follows_its_list_permission(self):
        item = _item(item_type=MenuItem.RESOURCE, route_name="",
                     content_type=ContentType.objects.get_for_model(Branch))

        assert MenuPermissionService.can_see(item, {"list_branch"}) is True
        assert MenuPermissionService.can_see(item, set()) is False


class TestAddRoute:

    def test_add_route_needs_its_permission(self):
        item = _item(add_route_name="add_x", add_permission_code="add_x")

        assert MenuPermissionService.can_add(item, {"add_x"}) is True
        assert MenuPermissionService.can_add(item, set()) is False

    def test_add_route_without_route_name_is_never_offered(self):
        item = _item(add_permission_code="add_x")

        assert MenuPermissionService.can_add(item, {"add_x"}) is False
