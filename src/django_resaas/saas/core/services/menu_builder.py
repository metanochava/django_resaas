"""MenuBuilder: the navigation tree from the database menus (MENU_IMPLEMENTATION_PROGRESS.md,
phase 8). Not wired to build_menus yet: nothing calls it in the running sidebar.

Output has the payload shape the frontend already reads (core/menus.py):
- top level, one entry per menu: {menu, icon, app, app_label, submenu};
- a leaf (page or resource): {menu, icon, route, add_route?, submenu: []};
- a group: {menu, icon, submenu};
- a direct link (Menu.is_direct_link): {menu, icon, app, app_label, route, submenu: []}.

Rules (section 5 and 7 of the plan):
- a node is kept only if it is visible: its own permission (MenuPermissionService)
  and, for a group, at least one visible descendant. Empty groups are dropped;
- hidden_menu_apps hides a menu when every module it is presented in is hidden;
- items are shown only in the modules they apply to (MenuRepository.item_applies);
- ordering is the repository's (order, then label/code);
- an invalid structure never fails the whole tree: a cycle or a node deeper than
  MAX_DEPTH is skipped and logged as a warning, the rest is still built.
"""
import logging

from django_resaas.saas.core.services.menu_permission_service import MenuPermissionService
from django_resaas.saas.core.services.menu_repository import MenuRepository
from django_resaas.saas.core.services.menu_validator import MAX_DEPTH
from django_resaas.saas.models.menu import MenuItem

logger = logging.getLogger("django_resaas.menus")


def _leaf(item, perms):
    node = {"menu": item.label, "icon": item.icon, "route": item.route_name, "submenu": []}
    if MenuPermissionService.can_add(item, perms):
        node["add_route"] = item.add_route_name
    return node


class MenuBuilder:

    @classmethod
    def build(cls, request, app_names=None):
        """The tree for the request's current profile (effective permissions)."""
        perms, hidden_apps = MenuPermissionService.effective_permissions(request)
        return cls.build_from(perms, hidden_apps=hidden_apps, app_names=app_names)

    @classmethod
    def build_from(cls, perms, hidden_apps=frozenset(), app_names=None):
        """The tree for explicit permissions (lower case codenames). Used by build()
        and by tests, so the tree logic does not depend on a request."""
        menus = MenuRepository.active_menus(app_names)
        menu_ids = [menu.id for menu in menus]
        grouped = MenuRepository.items_by_parent(menu_ids)
        modules_of = MenuRepository.module_names_of_menus(menu_ids)
        hidden = {str(app).strip().lower() for app in hidden_apps}

        tree = []
        for menu in menus:
            module_names = sorted(modules_of.get(menu.id, set()))
            if menu.is_direct_link:
                # a direct link keeps the legacy shape (route at the top level) and,
                # as in the legacy build_menus, it is not hidden by hidden_menu_apps
                link = next((n for n in cls._children(menu, None, grouped, perms, app_names,
                                                       frozenset(), 0) if "route" in n), None)
                if link is not None:
                    name = module_names[0] if module_names else None
                    tree.append({"menu": menu.label, "icon": menu.icon, "app": name, "app_label": name,
                                 "route": link["route"], "submenu": []})
                continue
            if module_names and all(str(name).strip().lower() in hidden for name in module_names):
                continue
            children = cls._children(menu, None, grouped, perms, app_names, path=frozenset(), depth=0)
            if not children:
                continue
            tree.append({
                "menu": menu.label,
                "icon": menu.icon,
                "app": module_names[0] if module_names else None,
                "app_label": module_names[0] if module_names else None,
                "submenu": children,
            })
        return tree

    @classmethod
    def _children(cls, menu, parent_id, grouped, perms, app_names, path, depth):
        if depth > MAX_DEPTH:
            logger.warning("menu %s: nesting deeper than %s levels skipped", menu.code, MAX_DEPTH)
            return []

        nodes = []
        for item in grouped.get((menu.id, parent_id), []):
            if not MenuRepository.item_applies(item, app_names):
                continue
            if item.id in path:
                logger.warning("menu %s: cycle at item %s skipped", menu.code, item.id)
                continue
            node = cls._node(menu, item, grouped, perms, app_names, path | {item.id}, depth)
            if node is not None:
                nodes.append(node)
        return nodes

    @classmethod
    def _node(cls, menu, item, grouped, perms, app_names, path, depth):
        if item.item_type == MenuItem.GROUP:
            if not MenuPermissionService.can_see(item, perms):
                return None
            children = cls._children(menu, item.id, grouped, perms, app_names, path, depth + 1)
            if not children:
                return None
            return {"menu": item.label, "icon": item.icon, "submenu": children}

        if not MenuPermissionService.can_see(item, perms):
            return None
        if not item.route_name:
            logger.warning("menu %s: item %s has no route, skipped", menu.code, item.id)
            return None
        return _leaf(item, perms)
