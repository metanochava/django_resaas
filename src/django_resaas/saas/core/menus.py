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
    link = (BranchUserGroup.objects.filter(user_id=request.user.id, branch_id=branch_id, group_id=group_id, state="Active")
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


def filter_menu_by_permission(menu_list, user_perms):
    result = []

    user_perms = {
        str(permission).strip().lower()
        for permission in (user_perms or [])
        if permission
    }

    for item in menu_list:
        role = item.get("role")
        add_role = item.get("add_role")

        role = str(role).strip().lower() if role else None
        add_role = str(add_role).strip().lower() if add_role else None

        sub = filter_menu_by_permission(
            item.get("submenu", []),
            user_perms
        )

        has_perm = role is None or role in user_perms
        add_perm = add_role is None or add_role in user_perms

        if has_perm or sub:
            new = {
                key: value
                for key, value in item.items()
                if key not in {"role", "add_role"}
            }

            if not add_perm:
                new.pop("add_route", None)

            if sub:
                new["submenu"] = sub
            else:
                new.pop("submenu", None)

            result.append(new)

    return result


def build_menus(request):
    """The sidebar of the CURRENT profile (request.entity_type_id/branch_id/
    group_id from the RESAAS context): every active, entitled module's
    sidebar.py filtered by the profile's menu permissions. Used by
    users/{id}/menus/ and resaas/boot/."""
    from django.apps import apps
    import importlib
    from django_resaas.saas.core.entitlements import has_module


    tipo_id = getattr(request, "entity_type_id", None)

    if not tipo_id:
        return []

    # =====================================================
    # EFFECTIVE PERMISSIONS FOR CURRENT BRANCH/GROUP
    #
    # Deliberadamente SEM bypass de is_superuser aqui: o menu
    # reflecte sempre o grupo/perfil actualmente seleccionado
    # (BranchUserGroup), mesmo para superuser. Sem isto, trocar o
    # perfil activo para "Guest" (BootstrapService já associa o
    # criador da entity a "Guest" além do grupo admin escolhido,
    # precisamente para servir de pré-visualização) nunca mudava o
    # menu de um superuser - via sempre tudo, independentemente do
    # perfil seleccionado. Um superuser continua a ver tudo nas
    # entities/branches onde estiver em "Root" (que já tem todas
    # as permissões via create_model_permissions), sem precisar de
    # nenhum caso especial aqui.
    # =====================================================
    # the menu shows what the profile may open, minus what it hides
    menu_perms, hidden_apps = menu_permissions(request)
    active_apps = active_app_names(tipo_id)

    def module_active(app_config):
        return is_active_app(app_config, active_apps)

    # =====================================================
    # BUILD MENUS
    # =====================================================
    MENUS = []

    # the same order as the module catalogue (list_app): the platform's
    # modules first (django_resaas, django_resaas.<x>), then the
    # business modules in settings.MY_APPS order; anything else last
    from django.conf import settings

    my_apps = list(getattr(settings, "MY_APPS", []) or [])

    def menu_order(app_config):
        name = str(app_config.name or "").lower()
        platform = name.startswith("django_resaas") or "." in name
        position = my_apps.index(app_config.name) if app_config.name in my_apps else len(my_apps)
        return (0 if platform else 1, position)

    for app_config in sorted(apps.get_app_configs(), key=menu_order):

        if not module_active(app_config):
            continue

        # entitlements: a module outside what the tenant is entitled to has no menu
        if not has_module(request, app_config.label):
            continue

        # the module's eye hides its menu groups; its direct links follow
        # only their own permission's eye (hidden_menu_permissions)
        app_hidden = str(app_config.label).strip().lower() in hidden_apps

        module_name = f"{app_config.name}.sidebar"

        try:
            sidebar = importlib.import_module(module_name)

        except ModuleNotFoundError as exc:
            # Ignore only when this app has no sidebar.
            # If the sidebar exists but one of its internal imports fails,
            # re-raise the real error instead of hiding it.
            if exc.name == module_name:
                continue
            raise

        ALL = getattr(sidebar, "ALL", [])

        if not isinstance(ALL, (list, tuple)):
            continue

        for menu_config in ALL:

            if not isinstance(menu_config, dict):
                continue

            MENU = menu_config.get("MENU")
            ICON = menu_config.get("ICON", "menu")
            SUBMENUS = menu_config.get("SUBMENUS", [])
            ROUTE = menu_config.get("ROUTE")

            # a direct top-level link (no submenu): {"MENU", "ICON",
            # "ROUTE", "ROLE"}. It needs its permission - a link without
            # ROLE is never shown (fail closed).
            if MENU and ROUTE and not SUBMENUS:
                role = str(menu_config.get("ROLE") or "").strip().lower()
                if role and role in menu_perms:
                    MENUS.append({
                        "menu": MENU,
                        "icon": ICON,
                        "app": app_config.name,
                        "app_label": app_config.label,
                        "route": ROUTE,
                        "submenu": [],
                    })
                continue

            if not MENU or not SUBMENUS or app_hidden:
                continue

            filtered_submenus = filter_menu_by_permission(
                SUBMENUS,
                menu_perms
            )

            if not filtered_submenus:
                continue

            MENUS.append({
                "menu": MENU,
                "icon": ICON,
                "app": app_config.name,
                "app_label": app_config.label,
                "submenu": filtered_submenus,
            })

    return MENUS
