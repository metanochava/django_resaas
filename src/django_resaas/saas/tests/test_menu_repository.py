"""MenuRepository (phase 6): read only; module rules; fixed query count."""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from django_resaas.saas.core.services.menu_repository import MenuRepository
from django_resaas.saas.models.app import App
from django_resaas.saas.models.menu import Menu, MenuItem, MenuItemModule, MenuModule

pytestmark = pytest.mark.django_db


def _menu(code, **extra):
    return Menu.objects.create(code=code, name=code, label=code, **extra)


class TestActiveMenus:

    def test_inactive_menus_are_excluded(self):
        _menu("on")
        _menu("off", state="Inactive")

        codes = [m.code for m in MenuRepository.active_menus()]

        assert codes == ["on"]

    def test_menu_without_module_is_included_for_any_module(self):
        _menu("shared")

        assert [m.code for m in MenuRepository.active_menus(["hr"])] == ["shared"]

    def test_menu_is_presented_only_in_its_modules(self):
        hr = App.objects.create(name="hr", state="Active")
        sales = App.objects.create(name="sales", state="Active")
        hr_menu = _menu("hr-menu")
        MenuModule.objects.create(menu=hr_menu, app=hr)
        sales_menu = _menu("sales-menu")
        MenuModule.objects.create(menu=sales_menu, app=sales)

        codes = {m.code for m in MenuRepository.active_menus(["hr"])}

        assert codes == {"hr-menu"}

    def test_menu_in_two_modules_is_returned_once(self):
        hr = App.objects.create(name="hr", state="Active")
        saude = App.objects.create(name="saude", state="Active")
        menu = _menu("both")
        MenuModule.objects.create(menu=menu, app=hr)
        MenuModule.objects.create(menu=menu, app=saude)

        menus = MenuRepository.active_menus(["hr", "saude"])

        assert [m.code for m in menus] == ["both"]

    def test_none_means_no_module_filter(self):
        hr = App.objects.create(name="hr", state="Active")
        menu = _menu("restricted")
        MenuModule.objects.create(menu=menu, app=hr)

        assert [m.code for m in MenuRepository.active_menus(None)] == ["restricted"]


class TestItems:

    def test_items_are_grouped_by_parent_in_order(self):
        menu = _menu("tree")
        group = MenuItem.objects.create(menu=menu, label="Group", item_type=MenuItem.GROUP, order=1)
        MenuItem.objects.create(menu=menu, label="top", item_type=MenuItem.PAGE, route_name="t", order=0)
        MenuItem.objects.create(menu=menu, parent=group, label="b", item_type=MenuItem.PAGE, route_name="b", order=2)
        MenuItem.objects.create(menu=menu, parent=group, label="a", item_type=MenuItem.PAGE, route_name="a", order=1)

        grouped = MenuRepository.items_by_parent([menu.id])

        assert [i.label for i in grouped[(menu.id, None)]] == ["top", "Group"]
        assert [i.label for i in grouped[(menu.id, group.id)]] == ["a", "b"]

    def test_inactive_items_are_excluded(self):
        menu = _menu("inactive-items")
        MenuItem.objects.create(menu=menu, label="on", item_type=MenuItem.PAGE, route_name="on")
        MenuItem.objects.create(menu=menu, label="off", item_type=MenuItem.PAGE, route_name="off", state="Inactive")

        grouped = MenuRepository.items_by_parent([menu.id])

        assert [i.label for i in grouped[(menu.id, None)]] == ["on"]

    def test_item_without_restriction_applies_everywhere(self):
        menu = _menu("plain")
        item = MenuItem.objects.create(menu=menu, label="x", item_type=MenuItem.PAGE, route_name="x")

        assert MenuRepository.item_applies(item, ["sales"]) is True

    def test_item_restricted_to_a_module(self):
        menu = _menu("restrict")
        hr = App.objects.create(name="hr", state="Active")
        item = MenuItem.objects.create(menu=menu, label="Payroll", item_type=MenuItem.PAGE, route_name="p")
        MenuItemModule.objects.create(item=item, app=hr)
        grouped = MenuRepository.items_by_parent([menu.id])
        listed = grouped[(menu.id, None)][0]

        assert MenuRepository.item_applies(listed, ["hr"]) is True
        assert MenuRepository.item_applies(listed, ["sales"]) is False

    def test_query_count_does_not_grow_with_items(self):
        menus = [_menu(f"q{i}") for i in range(3)]
        for menu in menus:
            for n in range(10):
                parent = MenuItem.objects.create(menu=menu, label=f"g{n}", item_type=MenuItem.GROUP)
                MenuItem.objects.create(menu=menu, parent=parent, label="c", item_type=MenuItem.PAGE, route_name="c")

        with CaptureQueriesContext(connection) as one:
            MenuRepository.items_by_parent([menus[0].id])
        with CaptureQueriesContext(connection) as all_of_them:
            MenuRepository.items_by_parent([m.id for m in menus])

        # the same fixed set of queries for 1 or 3 menus (no per-item or per-menu query)
        assert len(all_of_them.captured_queries) == len(one.captured_queries)
        assert len(one.captured_queries) <= 3
