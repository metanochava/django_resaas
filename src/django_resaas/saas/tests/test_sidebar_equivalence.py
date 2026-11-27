"""Phase 12: the migrated database menus show what the sidebar.py menus showed.

For each sidebar menu (with SUBMENUS) and each permission set, the legacy tree
(core/menus.py::filter_menu_by_permission) is compared with the database tree
(MenuBuilder) after `migrate_sidebars --apply`. Compared: labels, routes,
add routes and nesting. Icons are compared too.
"""
import importlib

import pytest
from django.apps import apps
from django.core.management import call_command

from django_resaas.saas.core.menus import filter_menu_by_permission
from django_resaas.saas.core.services.menu_builder import MenuBuilder

pytestmark = pytest.mark.django_db


def _normal(nodes):
    """Comparable shape: label, icon, route, add_route, children (recursive)."""
    out = []
    for node in nodes or []:
        out.append({
            "label": node.get("menu"),
            "icon": node.get("icon"),
            "route": node.get("route") or "",
            "add_route": node.get("add_route") or "",
            "children": _normal(node.get("submenu")),
        })
    return out


def _legacy_menus(perms):
    """Legacy sidebar entries (SUBMENUS only) per app label."""
    result = {}
    for app_config in apps.get_app_configs():
        try:
            module = importlib.import_module(f"{app_config.name}.sidebar")
        except ModuleNotFoundError:
            continue
        for config in getattr(module, "ALL", []) or []:
            if not config.get("SUBMENUS"):
                continue
            filtered = filter_menu_by_permission(config["SUBMENUS"], perms)
            result[(app_config.label, config["MENU"])] = _normal(filtered)
    return result


def _database_menus(perms):
    result = {}
    for entry in MenuBuilder.build_from(perms):
        result[(entry["app_label"], entry["menu"])] = _normal(entry["submenu"])
    return result


PROFILES = {
    "nothing": set(),
    "reception-like": {"list_paciente", "add_paciente", "view_agenda"},
    "everything": None,  # filled with every role the sidebars declare
}


def _all_roles():
    roles = set()

    def walk(nodes):
        for node in nodes or []:
            for key in ("role", "add_role"):
                if node.get(key):
                    roles.add(node[key].strip().lower())
            walk(node.get("submenu"))

    for app_config in apps.get_app_configs():
        try:
            module = importlib.import_module(f"{app_config.name}.sidebar")
        except ModuleNotFoundError:
            continue
        for config in getattr(module, "ALL", []) or []:
            walk(config.get("SUBMENUS"))
    return roles


class TestSidebarEquivalence:

    @pytest.fixture(autouse=True)
    def _migrated(self, db):
        call_command("migrate_sidebars", "--apply", verbosity=0)

    @pytest.mark.parametrize("profile", ["nothing", "reception-like", "everything"])
    def test_same_tree_for_each_profile(self, profile):
        perms = PROFILES[profile] if PROFILES[profile] is not None else _all_roles()

        # a menu with nothing visible is hidden by build_menus in both sources
        legacy = {k: v for k, v in _legacy_menus(perms).items() if v}
        database = {k: v for k, v in _database_menus(perms).items() if v}

        mismatched = {key for key in set(legacy) | set(database) if legacy.get(key) != database.get(key)}
        assert mismatched == set(), f"differences for {sorted(mismatched)}"

    def test_migration_is_idempotent(self):
        from django_resaas.saas.models.menu import MenuItem, Menu

        before = (Menu.objects.count(), MenuItem.objects.count())
        call_command("migrate_sidebars", "--apply", verbosity=0)
        after = (Menu.objects.count(), MenuItem.objects.count())

        assert before == after

    def test_dry_run_writes_nothing(self):
        from django_resaas.saas.models.menu import Menu

        Menu.objects.all().delete()
        call_command("migrate_sidebars", verbosity=0)

        assert Menu.objects.count() == 0
