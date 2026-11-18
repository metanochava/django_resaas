"""The bottom tab bar of phone-sized screens (WhatsApp-like), per Entity Type
with an Entity override, filtered by the CURRENT profile.

- The Entity's own active tabs (EntityMobileTab) replace its Entity Type's
  (EntityTypeMobileTab) when it has any.
- A tab is shown only when its `permission` is among the profile's menu
  permissions (core/menus.menu_permissions: effective, minus the hidden
  ones), its app is active for the Entity Type and entitled (has_module) -
  the same rules as the sidebar. The frontend never decides.
- At most MAX_TABS, in order; the frontend adds "More" (the drawer).

Each module may offer candidates in `<app>/mobile_tabs.py`:

    TABS = [{"label": "Lessons", "icon": "history_edu", "route": "view_own_lesson",
             "permission": "view_own_lesson", "order": 10}, ...]

seed_entity_type() copies the candidates of the Entity Type's active apps
(the core never imports a module by name: it looks for that file).
"""
import importlib

from django.apps import apps

from django_resaas.saas.core.menus import active_app_names, is_active_app, menu_permissions
from django_resaas.saas.models.mobile_tab import EntityMobileTab, EntityTypeMobileTab

MAX_TABS = 4


def _rows(request):
    entity_id = getattr(request, "entity_id", None)
    own = EntityMobileTab.objects.filter(entity_id=entity_id, active=True) if entity_id else EntityMobileTab.objects.none()
    if own.exists():
        return list(own)
    entity_type_id = getattr(request, "entity_type_id", None)
    if not entity_type_id:
        return []
    return list(EntityTypeMobileTab.objects.filter(entity_type_id=entity_type_id, active=True))


def tabs_for(request):
    from django_resaas.saas.core.entitlements import has_module

    entity_type_id = getattr(request, "entity_type_id", None)
    if not entity_type_id:
        return []
    perms, hidden_apps = menu_permissions(request)
    active = active_app_names(entity_type_id)
    configs = {config.label: config for config in apps.get_app_configs()}
    shown = []
    for tab in _rows(request):
        label = str(tab.app or "").strip()
        config = configs.get(label)
        if config is None or not is_active_app(config, active) or not has_module(request, label):
            continue
        if label.lower() in hidden_apps or str(tab.permission).strip().lower() not in perms:
            continue
        shown.append({"label": tab.label, "icon": tab.icon, "route": tab.route, "app": label})
        if len(shown) == MAX_TABS:
            break
    return shown


def candidates(app_config):
    module_name = f"{app_config.name}.mobile_tabs"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return []
        raise
    return [dict(tab, app=app_config.label) for tab in getattr(module, "TABS", []) or [] if isinstance(tab, dict)]


def seed_entity_type(entity_type, replace=False):
    """The candidates of the Entity Type's active apps as its tabs; an Entity
    Type that already has tabs keeps them (unless replace). Idempotent."""
    if EntityTypeMobileTab.objects.filter(entity_type=entity_type).exists() and not replace:
        return 0
    if replace:
        EntityTypeMobileTab.objects.filter(entity_type=entity_type).delete()
    active = active_app_names(entity_type.id)
    made = 0
    for config in apps.get_app_configs():
        if not is_active_app(config, active):
            continue
        for tab in candidates(config):
            _, created = EntityTypeMobileTab.objects.get_or_create(
                entity_type=entity_type, route=tab["route"],
                defaults={"label": tab["label"], "icon": tab.get("icon", "circle"), "permission": tab["permission"],
                          "app": tab["app"], "order": tab.get("order", 10)})
            made += created
    return made
