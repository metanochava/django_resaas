"""MenuBuilder (phase 8): the recursive tree from database menus. Not wired to build_menus."""
from types import SimpleNamespace

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from django_resaas.saas.core.services.menu_builder import MenuBuilder
from django_resaas.saas.core.services.menu_validator import MAX_DEPTH
from django_resaas.saas.models.app import App
from django_resaas.saas.models.menu import Menu, MenuItem, MenuModule

pytestmark = pytest.mark.django_db


def _menu(code, **extra):
    return Menu.objects.create(code=code, name=code, label=code.title(), icon="menu", **extra)


def _page(menu, label, perm, parent=None, route=None, **extra):
    return MenuItem.objects.create(
        menu=menu, parent=parent, label=label, item_type=MenuItem.PAGE,
        route_name=route or label.lower(), permission_code=perm, icon="i", **extra,
    )


def _group(menu, label, parent=None, perm="", **extra):
    return MenuItem.objects.create(
        menu=menu, parent=parent, label=label, item_type=MenuItem.GROUP, permission_code=perm, icon="g", **extra,
    )


class TestPayloadShape:

    def test_leaf_and_group_shape(self):
        menu = _menu("admin")
        group = _group(menu, "Organisation")
        _page(menu, "Departments", "view_department", parent=group, route="departments")

        tree = MenuBuilder.build_from({"view_department"})

        assert tree == [{
            "menu": "Admin",
            "icon": "menu",
            "app": None,
            "app_label": None,
            "submenu": [{
                "menu": "Organisation",
                "icon": "g",
                "submenu": [{"menu": "Departments", "icon": "i", "route": "departments", "submenu": []}],
            }],
        }]

    def test_add_route_only_with_its_permission(self):
        menu = _menu("crud")
        _page(menu, "Patient", "list_patient", route="list_patient",
              add_route_name="add_patient", add_permission_code="add_patient")

        with_add = MenuBuilder.build_from({"list_patient", "add_patient"})
        without_add = MenuBuilder.build_from({"list_patient"})

        assert with_add[0]["submenu"][0]["add_route"] == "add_patient"
        assert "add_route" not in without_add[0]["submenu"][0]


class TestVisibility:

    def test_page_without_permission_is_hidden_and_menu_is_dropped(self):
        menu = _menu("hidden")
        _page(menu, "Secret", "view_secret")

        assert MenuBuilder.build_from({"view_other"}) == []

    def test_group_without_visible_children_is_dropped(self):
        menu = _menu("empty-group")
        group = _group(menu, "Reports")
        _page(menu, "Finance", "view_finance", parent=group)
        _page(menu, "Visible", "view_visible")

        tree = MenuBuilder.build_from({"view_visible"})

        labels = [child["menu"] for child in tree[0]["submenu"]]
        assert labels == ["Visible"]

    def test_group_with_one_visible_descendant_is_shown(self):
        menu = _menu("deep-visible")
        level1 = _group(menu, "L1")
        level2 = _group(menu, "L2", parent=level1)
        _page(menu, "Leaf", "view_leaf", parent=level2)

        tree = MenuBuilder.build_from({"view_leaf"})

        assert tree[0]["submenu"][0]["submenu"][0]["submenu"][0]["menu"] == "Leaf"

    def test_group_with_its_own_permission_needs_it(self):
        menu = _menu("gated")
        admin = _group(menu, "Admin only", perm="view_admin")
        _page(menu, "Child", "view_child", parent=admin)
        _page(menu, "Open", "view_open")

        without_group_perm = MenuBuilder.build_from({"view_open", "view_child"})
        with_group_perm = MenuBuilder.build_from({"view_open", "view_child", "view_admin"})

        assert [c["menu"] for c in without_group_perm[0]["submenu"]] == ["Open"]
        assert [c["menu"] for c in with_group_perm[0]["submenu"]] == ["Admin only", "Open"]

    def test_no_branch_or_group_gives_an_empty_tree(self):
        menu = _menu("no-profile")
        _page(menu, "Anything", "view_anything")
        request = SimpleNamespace(user=SimpleNamespace(id=1, is_superuser=True), branch_id=None, group_id=None)

        assert MenuBuilder.build(request) == []


class TestModules:

    def test_menu_hidden_when_all_its_modules_are_hidden(self):
        hr = App.objects.create(name="hr", state="Active")
        menu = _menu("hr-only")
        MenuModule.objects.create(menu=menu, app=hr)
        _page(menu, "Payroll", "view_payroll")

        tree = MenuBuilder.build_from({"view_payroll"}, hidden_apps={"hr"})

        assert tree == []

    def test_menu_kept_when_one_of_its_modules_is_visible(self):
        hr = App.objects.create(name="hr", state="Active")
        saude = App.objects.create(name="saude", state="Active")
        menu = _menu("shared-menu")
        MenuModule.objects.create(menu=menu, app=hr)
        MenuModule.objects.create(menu=menu, app=saude)
        _page(menu, "Shared", "view_shared")

        tree = MenuBuilder.build_from({"view_shared"}, hidden_apps={"hr"})

        assert tree and tree[0]["submenu"][0]["menu"] == "Shared"

    def test_item_restricted_to_other_module_is_not_built(self):
        from django_resaas.saas.models.menu import MenuItemModule

        sales = App.objects.create(name="sales", state="Active")
        menu = _menu("restricted-items")
        item = _page(menu, "Invoices", "view_invoice")
        MenuItemModule.objects.create(item=item, app=sales)

        assert MenuBuilder.build_from({"view_invoice"}, app_names=["hr"]) == []
        assert MenuBuilder.build_from({"view_invoice"}, app_names=["sales"])[0]["submenu"][0]["menu"] == "Invoices"


class TestRobustness:

    def test_cycle_among_unreachable_items_does_not_hang(self):
        menu = _menu("cycle")
        a = _group(menu, "A")
        b = _group(menu, "B", parent=a)
        a.parent = b
        a.save(update_fields=["parent"])
        _page(menu, "Safe", "view_safe")

        tree = MenuBuilder.build_from({"view_safe"})

        assert tree[0]["submenu"][0]["menu"] == "Safe"

    def test_nesting_beyond_the_limit_is_not_built(self):
        menu = _menu("too-deep")
        parent = None
        for depth in range(MAX_DEPTH + 3):
            parent = _group(menu, f"L{depth}", parent=parent)
        _page(menu, "Bottom", "view_bottom", parent=parent)

        tree = MenuBuilder.build_from({"view_bottom"})

        flat = str(tree)
        assert "Bottom" not in flat

    def test_query_count_does_not_grow_with_menus(self):
        menus = [_menu(f"q{i}") for i in range(3)]
        for menu in menus:
            group = _group(menu, "G")
            for n in range(5):
                _page(menu, f"P{n}", f"view_p{n}", parent=group)
        perms = {f"view_p{n}" for n in range(5)}

        with CaptureQueriesContext(connection) as one:
            MenuBuilder.build_from(perms, app_names=None)
        Menu.objects.exclude(id=menus[0].id).delete()
        with CaptureQueriesContext(connection) as fewer:
            MenuBuilder.build_from(perms, app_names=None)

        assert len(fewer.captured_queries) <= len(one.captured_queries)
