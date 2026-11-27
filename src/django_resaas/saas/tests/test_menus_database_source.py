"""build_menus database source (phase 9): database menus replace the sidebar.py of
the apps they are presented in; every other app keeps its sidebar.py.
With no database menus nothing is covered, so the output is the sidebar path."""
import pytest

from django_resaas.saas.core.menus import _database_menus
from django_resaas.saas.models.app import App
from django_resaas.saas.models.menu import Menu, MenuItem, MenuItemModule, MenuModule

pytestmark = pytest.mark.django_db


def _menu(code, label=None, icon="menu"):
    return Menu.objects.create(code=code, name=code, label=label or code.title(), icon=icon)


def _page(menu, label, perm, route, **extra):
    return MenuItem.objects.create(menu=menu, label=label, item_type=MenuItem.PAGE,
                                   route_name=route, permission_code=perm, **extra)


class TestNoDatabaseMenus:

    def test_nothing_is_covered_without_menus(self):
        covered, by_app = _database_menus({"view_x"}, frozenset())

        assert covered == frozenset()
        assert by_app == {}

    def test_a_menu_without_module_covers_nothing(self):
        menu = _menu("unrestricted")
        _page(menu, "Anything", "view_x", "x")

        covered, by_app = _database_menus({"view_x"}, frozenset())

        assert covered == frozenset()
        assert by_app == {}


class TestCoveredApps:

    def test_app_with_a_database_menu_is_covered_with_its_tree(self):
        hr = App.objects.create(name="hr", state="Active")
        menu = _menu("hr-admin", label="HR Admin", icon="badge")
        MenuModule.objects.create(menu=menu, app=hr)
        _page(menu, "Employees", "view_employee", "list_employee")

        covered, by_app = _database_menus({"view_employee"}, frozenset())

        assert covered == {"hr"}
        assert by_app["hr"] == [{
            "menu": "HR Admin",
            "icon": "badge",
            "app": "hr",
            "app_label": "hr",
            "submenu": [{"menu": "Employees", "icon": "", "route": "list_employee", "submenu": []}],
        }]

    def test_app_without_a_visible_item_is_covered_but_empty(self):
        hr = App.objects.create(name="hr", state="Active")
        menu = _menu("hr-hidden")
        MenuModule.objects.create(menu=menu, app=hr)
        _page(menu, "Payroll", "view_payroll", "payroll")

        covered, by_app = _database_menus({"view_other"}, frozenset())

        assert covered == {"hr"}
        assert by_app.get("hr", []) == []

    def test_hidden_menu_app_yields_no_entries(self):
        hr = App.objects.create(name="hr", state="Active")
        menu = _menu("hr-hidden-app")
        MenuModule.objects.create(menu=menu, app=hr)
        _page(menu, "Employees", "view_employee", "list_employee")

        covered, by_app = _database_menus({"view_employee"}, frozenset({"hr"}))

        assert covered == {"hr"}
        assert by_app.get("hr", []) == []

    def test_other_apps_are_not_covered(self):
        hr = App.objects.create(name="hr", state="Active")
        App.objects.create(name="sales", state="Active")
        menu = _menu("only-hr")
        MenuModule.objects.create(menu=menu, app=hr)
        _page(menu, "Employees", "view_employee", "list_employee")

        covered, _ = _database_menus({"view_employee"}, frozenset())

        assert "sales" not in covered

    def test_inactive_menu_does_not_cover_its_app(self):
        hr = App.objects.create(name="hr", state="Active")
        menu = _menu("inactive-hr", )
        menu.state = "Inactive"
        menu.save(update_fields=["state"])
        MenuModule.objects.create(menu=menu, app=hr)
        _page(menu, "Employees", "view_employee", "list_employee")

        covered, by_app = _database_menus({"view_employee"}, frozenset())

        assert covered == frozenset()
        assert by_app == {}

    def test_item_restricted_to_another_module_is_not_in_this_app(self):
        hr = App.objects.create(name="hr", state="Active")
        saude = App.objects.create(name="saude", state="Active")
        menu = _menu("shared")
        MenuModule.objects.create(menu=menu, app=hr)
        MenuModule.objects.create(menu=menu, app=saude)
        item = _page(menu, "Clinic only", "view_clinic", "clinic")
        MenuItemModule.objects.create(item=item, app=saude)

        covered, by_app = _database_menus({"view_clinic"}, frozenset())

        assert covered == {"hr", "saude"}
        assert by_app["hr"] == []
        assert by_app["saude"][0]["submenu"][0]["menu"] == "Clinic only"
