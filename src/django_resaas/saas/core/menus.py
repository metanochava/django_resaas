"""The permissions the sidebars (`<app>/sidebar.py`, read by
UserAPIView.menus) use as menu entries: the ROLE of a direct link and the
`role` / `add_role` of every submenu item. The Permissions modal shows a
menu-visibility toggle only for these (Group.hidden_menu_permissions)."""
import importlib
from functools import lru_cache

from django.apps import apps


def _collect(items, roles):
    for item in items or []:
        if not isinstance(item, dict):
            continue
        for key in ("role", "add_role"):
            if item.get(key):
                roles.add(str(item[key]).strip().lower())
        _collect(item.get("submenu"), roles)


@lru_cache(maxsize=1)
def menu_roles():
    roles = set()
    for app_config in apps.get_app_configs():
        module_name = f"{app_config.name}.sidebar"
        try:
            sidebar = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                continue
            raise
        for menu_config in getattr(sidebar, "ALL", []) or []:
            if not isinstance(menu_config, dict):
                continue
            if menu_config.get("ROLE"):
                roles.add(str(menu_config["ROLE"]).strip().lower())
            _collect(menu_config.get("SUBMENUS"), roles)
    return frozenset(roles)
