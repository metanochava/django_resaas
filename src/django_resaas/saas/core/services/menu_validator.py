"""MenuValidator: finds broken menu configuration without failing (MENU_IMPLEMENTATION_PROGRESS.md, phase 5).

Read only. It returns a list of MenuIssue; it never raises for bad data, never
changes a row and is not called by build_menus yet. The Django start-up is not
affected. The rules follow section 9 of the progress plan: each problem is
reported with enough context to fix it, and the rest of the configuration is
still checked.

Severity:
- "error": the item cannot work as configured (missing model, missing route,
  cycle, parent of another menu, ...).
- "warning": it works but is suspicious (empty menu, unknown permission code,
  inactive module).
"""
from dataclasses import dataclass

from django.contrib.auth.models import Permission

from django_resaas.saas.core.services.resource_registry import ResourceRegistry
from django_resaas.saas.models.menu import Menu, MenuItem, MenuItemModule, MenuModule

# A menu tree deeper than this is refused as a configuration error. Normal use
# (the 5-level example of the plan) is far below it; this only stops runaway
# nesting from making the menu builder slow.
MAX_DEPTH = 32


@dataclass(frozen=True)
class MenuIssue:
    severity: str
    code: str
    menu_code: str
    item_id: str
    message: str


def _issue(severity, code, menu, item, message):
    return MenuIssue(
        severity=severity,
        code=code,
        menu_code=menu.code if menu is not None else "",
        item_id=str(item.id) if item is not None else "",
        message=message,
    )


class MenuValidator:

    @classmethod
    def validate(cls):
        issues = []
        codenames = set(Permission.objects.values_list("codename", flat=True))
        items = list(MenuItem.objects.select_related("menu", "content_type", "parent"))

        for menu in Menu.objects.all():
            if not menu.items.exists():
                issues.append(_issue("warning", "empty_menu", menu, None, "The menu has no items."))

        for item in items:
            issues.extend(cls._check_item(item, codenames))

        issues.extend(cls._check_modules())
        return issues

    @classmethod
    def _check_item(cls, item, codenames):
        found = []
        menu = item.menu

        if item.parent_id is not None:
            found.extend(cls._check_parent(item, menu))

        if item.item_type == MenuItem.RESOURCE:
            found.extend(cls._check_resource(item, menu))
        elif item.item_type == MenuItem.PAGE:
            if not item.route_name:
                found.append(_issue("error", "missing_route", menu, item,
                                    "A page item needs a route_name."))
        elif item.item_type == MenuItem.GROUP and item.route_name:
            found.append(_issue("warning", "group_with_route", menu, item,
                                "A group does not open a route; route_name is ignored."))

        if item.permission_code and item.permission_code not in codenames:
            found.append(_issue("warning", "unknown_permission", menu, item,
                                f"Permission code '{item.permission_code}' does not exist."))

        if item.add_permission_code and not item.add_route_name:
            found.append(_issue("warning", "add_permission_without_route", menu, item,
                                "add_permission_code is set but add_route_name is empty."))

        found.extend(cls._check_depth_and_cycle(item, menu))
        return found

    @staticmethod
    def _check_parent(item, menu):
        parent = item.parent
        if parent is None or parent.deleted_at is not None:
            return [_issue("error", "invalid_parent", menu, item,
                           "The parent item does not exist (it was deleted).")]
        if parent.menu_id != item.menu_id:
            return [_issue("error", "parent_in_other_menu", menu, item,
                           "The parent item belongs to another menu.")]
        return []

    @staticmethod
    def _check_resource(item, menu):
        if item.content_type_id is None:
            return [_issue("error", "missing_model", menu, item,
                           "A resource item needs a content_type.")]
        model = item.content_type.model_class()
        if model is None:
            return [_issue("error", "missing_model", menu, item,
                           f"Content type {item.content_type_id} has no model class (removed?).")]
        info = ResourceRegistry.get(model._meta.app_label, model._meta.model_name)
        if info is None:
            return [_issue("error", "not_a_resource", menu, item,
                           f"{model._meta.label} does not declare class RESAAS with crud = True.")]
        if item.resource_action and item.resource_action not in info.routes:
            return [_issue("warning", "unknown_action", menu, item,
                           f"Action '{item.resource_action}' is not a route of {info.key}.")]
        return []

    @staticmethod
    def _check_depth_and_cycle(item, menu):
        seen = {item.id}
        depth = 0
        node = item
        while node.parent_id is not None:
            node = node.parent
            if node is None:
                break
            if node.id in seen:
                return [_issue("error", "cycle", menu, item,
                               "The parent chain of this item loops back to itself.")]
            seen.add(node.id)
            depth += 1
            if depth > MAX_DEPTH:
                return [_issue("error", "too_deep", menu, item,
                               f"Nesting deeper than {MAX_DEPTH} levels.")]
        return []

    @staticmethod
    def _check_modules():
        found = []
        for link in MenuModule.objects.select_related("menu", "app"):
            if link.app.state != "Active":
                found.append(_issue("warning", "inactive_module", link.menu, None,
                                    f"Module '{link.app.name}' is inactive for this menu."))
        for link in MenuItemModule.objects.select_related("item__menu", "app"):
            if link.app.state != "Active":
                found.append(_issue("warning", "inactive_module", link.item.menu, link.item,
                                    f"Module '{link.app.name}' is inactive for this item."))
        return found
