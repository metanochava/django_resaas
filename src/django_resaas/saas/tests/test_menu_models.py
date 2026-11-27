"""Database menus (phase 3): models only. No menu is built or served yet.

Covers: creation and default state, recursive parent/child depth, soft delete
(the row is kept, the default manager hides it), unique code, module
association and its uniqueness.
"""
import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction

from django_resaas.saas.models import Menu, MenuItem, MenuItemModule, MenuModule
from django_resaas.saas.models.app import App

pytestmark = pytest.mark.django_db


def _menu(code="admin"):
    return Menu.objects.create(code=code, name=code, label=code.title())


class TestMenuModel:

    def test_defaults_are_active_and_not_system(self):
        menu = _menu()

        assert menu.state == "Active"
        assert menu.is_system is False
        assert menu.order == 0

    def test_code_is_unique(self):
        _menu("dup")

        with pytest.raises(IntegrityError), transaction.atomic():
            _menu("dup")

    def test_soft_delete_keeps_the_row(self):
        menu = _menu("soft")

        menu.delete()

        assert not Menu.objects.filter(code="soft").exists()
        assert Menu.all_objects.filter(code="soft").exists()


class TestMenuItemHierarchy:

    def test_nested_groups_to_five_levels(self):
        menu = _menu("deep")
        parent = None
        levels = []
        for depth in range(5):
            item = MenuItem.objects.create(
                menu=menu, parent=parent, label=f"level {depth}", item_type=MenuItem.GROUP, order=depth
            )
            levels.append(item)
            parent = item

        leaf = levels[-1]
        ancestors = []
        node = leaf
        while node.parent_id is not None:
            node = node.parent
            ancestors.append(node)

        assert len(ancestors) == 4
        assert list(menu.items.filter(parent=levels[0]).values_list("label", flat=True)) == ["level 1"]

    def test_children_are_ordered_by_order(self):
        menu = _menu("order")
        group = MenuItem.objects.create(menu=menu, label="group", item_type=MenuItem.GROUP)
        MenuItem.objects.create(menu=menu, parent=group, label="second", order=2)
        MenuItem.objects.create(menu=menu, parent=group, label="first", order=1)

        labels = list(group.children.values_list("label", flat=True))

        assert labels == ["first", "second"]

    def test_resource_item_points_to_a_model(self):
        menu = _menu("res")
        content_type = ContentType.objects.get_for_model(Menu)

        item = MenuItem.objects.create(
            menu=menu, label="Menus", item_type=MenuItem.RESOURCE,
            content_type=content_type, resource_action="list", route_name="list_menu",
            permission_code="list_menu",
        )

        assert item.content_type.model_class() is Menu
        assert item.item_type == MenuItem.RESOURCE

    def test_deleting_a_parent_removes_its_children(self):
        menu = _menu("cascade")
        group = MenuItem.objects.create(menu=menu, label="group", item_type=MenuItem.GROUP)
        MenuItem.objects.create(menu=menu, parent=group, label="child")

        group.hard_delete()

        assert not MenuItem.all_objects.filter(label="child").exists()


class TestMenuModules:

    def test_menu_can_present_in_several_modules(self):
        menu = _menu("shared")
        hr = App.objects.create(name="hr", state="Active")
        saude = App.objects.create(name="saude", state="Active")

        MenuModule.objects.create(menu=menu, app=hr)
        MenuModule.objects.create(menu=menu, app=saude)

        assert menu.modules.count() == 2

    def test_same_menu_and_module_twice_is_rejected(self):
        menu = _menu("twice")
        app = App.objects.create(name="sales", state="Active")
        MenuModule.objects.create(menu=menu, app=app)

        with pytest.raises(IntegrityError), transaction.atomic():
            MenuModule.objects.create(menu=menu, app=app)

    def test_item_module_restriction(self):
        menu = _menu("restricted")
        item = MenuItem.objects.create(menu=menu, label="Payroll")
        app = App.objects.create(name="hr2", state="Active")

        MenuItemModule.objects.create(item=item, app=app)

        assert item.modules.get().app == app
