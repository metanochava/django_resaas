"""MenuValidator (phase 5): problems are reported, never raised, and the rest of
the configuration is still checked. Read only."""
import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError

from django_resaas.saas.core.services.menu_validator import MAX_DEPTH, MenuValidator
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.menu import Menu, MenuItem

pytestmark = pytest.mark.django_db


def _menu(code="m"):
    return Menu.objects.create(code=code, name=code, label=code)


def _codes(issues):
    return {issue.code for issue in issues}


class TestValidator:

    def test_no_menus_no_problems(self):
        assert MenuValidator.validate() == []

    def test_empty_menu_is_a_warning(self):
        _menu("empty")

        issues = MenuValidator.validate()

        assert [i.code for i in issues] == ["empty_menu"]
        assert issues[0].severity == "warning"

    def test_page_without_route_is_an_error(self):
        menu = _menu("page")
        MenuItem.objects.create(menu=menu, label="Dashboard", item_type=MenuItem.PAGE)

        issues = MenuValidator.validate()

        assert "missing_route" in _codes(issues)
        assert [i for i in issues if i.code == "missing_route"][0].severity == "error"

    def test_invalid_item_does_not_stop_the_others(self):
        menu = _menu("mixed")
        MenuItem.objects.create(menu=menu, label="broken", item_type=MenuItem.PAGE)
        MenuItem.objects.create(menu=menu, label="ok", item_type=MenuItem.PAGE, route_name="ok")
        MenuItem.objects.create(menu=menu, label="also broken", item_type=MenuItem.RESOURCE)

        issues = MenuValidator.validate()

        assert "missing_route" in _codes(issues)
        assert "missing_model" in _codes(issues)

    def test_resource_of_a_declared_model_is_valid(self):
        menu = _menu("resource-ok")
        MenuItem.objects.create(
            menu=menu, label="Branches", item_type=MenuItem.RESOURCE,
            content_type=ContentType.objects.get_for_model(Branch), resource_action="list",
        )

        assert _codes(MenuValidator.validate()) & {"missing_model", "not_a_resource", "unknown_action"} == set()

    def test_model_without_crud_declaration_is_not_a_resource(self):
        menu = _menu("not-resource")
        MenuItem.objects.create(
            menu=menu, label="Menus", item_type=MenuItem.RESOURCE,
            content_type=ContentType.objects.get_for_model(Menu),
        )

        assert "not_a_resource" in _codes(MenuValidator.validate())

    def test_resource_without_content_type_is_an_error(self):
        menu = _menu("no-ct")
        MenuItem.objects.create(menu=menu, label="x", item_type=MenuItem.RESOURCE)

        assert "missing_model" in _codes(MenuValidator.validate())

    def test_unknown_action_is_a_warning(self):
        menu = _menu("action")
        MenuItem.objects.create(
            menu=menu, label="Branches", item_type=MenuItem.RESOURCE,
            content_type=ContentType.objects.get_for_model(Branch), resource_action="explode",
        )

        issue = next(i for i in MenuValidator.validate() if i.code == "unknown_action")

        assert issue.severity == "warning"

    def test_unknown_permission_code_is_a_warning(self):
        menu = _menu("perm")
        MenuItem.objects.create(menu=menu, label="x", item_type=MenuItem.PAGE, route_name="x",
                                permission_code="no_such_permission_anywhere")

        issue = next(i for i in MenuValidator.validate() if i.code == "unknown_permission")

        assert issue.severity == "warning"

    def test_parent_deleted_is_an_error(self):
        menu = _menu("orphan")
        parent = MenuItem.objects.create(menu=menu, label="group", item_type=MenuItem.GROUP)
        MenuItem.objects.create(menu=menu, parent=parent, label="child", item_type=MenuItem.PAGE, route_name="c")
        parent.delete()

        assert "invalid_parent" in _codes(MenuValidator.validate())

    def test_parent_in_another_menu_is_an_error(self):
        first = _menu("first")
        second = _menu("second")
        parent = MenuItem.objects.create(menu=first, label="group", item_type=MenuItem.GROUP)
        MenuItem.objects.create(menu=second, parent=parent, label="child", item_type=MenuItem.PAGE, route_name="c")

        assert "parent_in_other_menu" in _codes(MenuValidator.validate())

    def test_cycle_is_detected(self):
        menu = _menu("cycle")
        a = MenuItem.objects.create(menu=menu, label="a", item_type=MenuItem.GROUP)
        b = MenuItem.objects.create(menu=menu, parent=a, label="b", item_type=MenuItem.GROUP)
        a.parent = b
        a.save(update_fields=["parent"])

        assert "cycle" in _codes(MenuValidator.validate())

    def test_nesting_beyond_the_limit_is_refused(self):
        menu = _menu("deep")
        parent = None
        for depth in range(MAX_DEPTH + 2):
            parent = MenuItem.objects.create(menu=menu, parent=parent, label=f"l{depth}", item_type=MenuItem.GROUP)

        assert "too_deep" in _codes(MenuValidator.validate())

    def test_nesting_within_the_limit_is_accepted(self):
        menu = _menu("five")
        parent = None
        for depth in range(5):
            parent = MenuItem.objects.create(menu=menu, parent=parent, label=f"l{depth}", item_type=MenuItem.GROUP)
        MenuItem.objects.create(menu=menu, parent=parent, label="leaf", item_type=MenuItem.PAGE, route_name="leaf")

        assert _codes(MenuValidator.validate()) & {"cycle", "too_deep", "invalid_parent"} == set()


class TestValidateMenusCommand:

    def test_reports_nothing_when_clean(self, capsys):
        call_command("validate_menus")

        assert "no problems found" in capsys.readouterr().out

    def test_errors_make_the_command_fail(self):
        menu = _menu("cmd")
        MenuItem.objects.create(menu=menu, label="x", item_type=MenuItem.PAGE)

        with pytest.raises(CommandError):
            call_command("validate_menus")
