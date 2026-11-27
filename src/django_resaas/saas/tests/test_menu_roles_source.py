"""Phase 17 prep: menu_roles() reads the database menus once they exist (sidebar.py
is the fallback when there are none), and a direct link keeps its legacy shape."""
import pytest

from django_resaas.saas.core.menus import _sidebar_menu_roles, menu_roles
from django_resaas.saas.core.services.menu_builder import MenuBuilder
from django_resaas.saas.models.app import App
from django_resaas.saas.models.menu import Menu, MenuItem, MenuModule

pytestmark = pytest.mark.django_db


def test_without_database_menus_the_sidebar_roles_are_used():
    assert Menu.objects.count() == 0

    assert menu_roles() == _sidebar_menu_roles()


def test_database_menus_are_the_source_once_they_exist():
    menu = Menu.objects.create(code="roles-src", name="r", label="R")
    MenuItem.objects.create(menu=menu, label="Pages", item_type=MenuItem.PAGE, route_name="pages",
                            permission_code="View_Page_Db", add_route_name="add_page",
                            add_permission_code="add_page_db")

    roles = menu_roles()

    assert "view_page_db" in roles
    assert "add_page_db" in roles
    assert "view_page_db" not in _sidebar_menu_roles()


def test_direct_link_keeps_its_legacy_shape():
    hr = App.objects.create(name="hr", state="Active")
    link = Menu.objects.create(code="link-x", name="l", label="Link X", icon="link", is_direct_link=True)
    MenuModule.objects.create(menu=link, app=hr)
    MenuItem.objects.create(menu=link, label="Link X", item_type=MenuItem.PAGE, route_name="link_x",
                            permission_code="view_link_x")

    tree = MenuBuilder.build_from({"view_link_x"}, app_names=["hr"])

    assert tree == [{"menu": "Link X", "icon": "link", "app": "hr", "app_label": "hr",
                     "route": "link_x", "submenu": []}]


def test_direct_link_hidden_without_its_permission():
    link = Menu.objects.create(code="link-hidden", name="l", label="Hidden", is_direct_link=True)
    MenuItem.objects.create(menu=link, label="Hidden", item_type=MenuItem.PAGE, route_name="hidden",
                            permission_code="view_hidden")

    assert MenuBuilder.build_from(set()) == []
