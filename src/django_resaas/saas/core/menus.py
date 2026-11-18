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


def menu_permissions(request):
    """What the CURRENT profile (BranchUserGroup of the request's branch and
    group) may see in a menu: (permissions minus the hidden ones, the
    hidden apps). No superuser bypass - the menu follows the selected
    profile (UserAPIView.menus explains why)."""
    from django_resaas.saas.models.branch_user_group import BranchUserGroup

    branch_id = getattr(request, "branch_id", None)
    group_id = getattr(request, "group_id", None)
    if not (branch_id and group_id):
        return set(), set()
    link = (BranchUserGroup.objects.filter(user_id=request.user.id, branch_id=branch_id, group_id=group_id)
            .select_related("group").first())
    if link is None:
        return set(), set()
    lower = lambda values: {str(v).strip().lower() for v in (values or [])}  # noqa: E731
    hidden_apps = lower(link.group.hidden_menu_apps)
    hidden_perms = lower(link.group.hidden_menu_permissions)
    perms = lower(link.group.permissions.values_list("codename", flat=True))
    return perms - hidden_perms, hidden_apps


def active_app_names(entity_type_id):
    from django_resaas.saas.models.entity_type_app import EntityTypeApp

    return {str(item.app.name).strip().lower()
            for item in EntityTypeApp.objects.filter(entity_type_id=entity_type_id).select_related("app")
            if item.app and item.app.name}


def is_active_app(app_config, active_apps):
    """App.name may be "past.app", "app", "past", "django_resaas.notifications"
    or "notifications"; AppConfig has the dotted name and the label."""
    app_name = str(app_config.name or "").strip().lower()
    app_label = str(app_config.label or "").strip().lower()
    parts = [part for part in app_name.split(".") if part]
    candidates = {app_name, app_label}
    if parts:
        candidates.update((parts[0], parts[-1]))
    candidates.discard("")
    return bool(candidates.intersection(active_apps))
