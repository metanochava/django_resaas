"""MenuPermissionService: which database menu items the current profile may see
(MENU_IMPLEMENTATION_PROGRESS.md, phase 7). Read only; not used by build_menus yet.

Nothing here creates a permission system. The profile's effective permissions
come from core/menus.py::menu_permissions (BranchUserGroup of the request, minus
hidden_menu_permissions, no superuser bypass), and the same rules as the
sidebar builder apply:

- a menu item never grants access: it only decides visibility; the API keeps
  validating each request;
- a page or resource item with no permission code is hidden (fail closed, as a
  direct link without ROLE is in core/menus.py);
- a resource item with no permission code follows the resource's own list
  permission (ResourceRegistry, phase 4);
- a group with no permission code is not restricted by itself: it is shown only
  when a visible descendant exists (the tree builder decides that, phase 8);
- an add route is offered only with its add permission (add_permission_code),
  exactly like add_route in core/menus.py.
"""
from django_resaas.saas.core.menus import menu_permissions
from django_resaas.saas.core.services.resource_registry import ResourceRegistry
from django_resaas.saas.models.menu import MenuItem


def _normal(code):
    return str(code or "").strip().lower()


class MenuPermissionService:

    @staticmethod
    def effective_permissions(request):
        """(permission codenames of the current profile, hidden app labels).
        Delegates to core/menus.py; no new permission lookup."""
        perms, hidden_apps = menu_permissions(request)
        return {_normal(code) for code in perms}, {_normal(app) for app in hidden_apps}

    @staticmethod
    def _required_code(item):
        """The codename that decides the item, or None when it is not restricted
        by a code of its own (see the module docstring)."""
        if item.permission_code:
            return _normal(item.permission_code)
        if item.item_type == MenuItem.RESOURCE and item.content_type_id is not None:
            model = item.content_type.model_class()
            if model is not None:
                info = ResourceRegistry.get(model._meta.app_label, model._meta.model_name)
                if info is not None:
                    return _normal(info.permissions.get("list"))
        return None

    @classmethod
    def can_see(cls, item, perms):
        """True when the profile (codename set `perms`, lower case) may see the
        item itself. Groups without a code return True: their children decide."""
        if item.item_type == MenuItem.GROUP and not item.permission_code:
            return True
        required = cls._required_code(item)
        if not required:
            return False
        return required in perms

    @classmethod
    def can_add(cls, item, perms):
        """True when the item's add route may be offered: it has an add route and
        the profile holds the add permission."""
        if not item.add_route_name or not item.add_permission_code:
            return False
        return _normal(item.add_permission_code) in perms
