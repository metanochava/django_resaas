"""Copy the sidebar.py declarations into the database menus (phase 11).

Idempotent: a menu is identified by its code (`sidebar.<app_label>`) and an item by
its menu, parent, label, item type and route, so running it again creates nothing
new. It never deletes rows and never edits a row created by hand (is_system marks
the ones it made). Dry run by default: pass --apply to write.

Mapping (sidebar.py -> database):
- ALL[i]: a Menu with code sidebar.<app>, label MENU, icon ICON, order i,
  linked to the app through MenuModule;
- SUBMENUS entries with submenu -> GROUP items;
- entries with route -> PAGE items (route_name, permission_code = role,
  add_route_name, add_permission_code = add_role);
- a top-level ROUTE with no SUBMENUS -> a menu with is_direct_link (its shape is a link, not a tree).
- a GROUP has no permission of its own: it is shown when a child is visible.
"""
import importlib

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from django_resaas.saas.models.app import App
from django_resaas.saas.models.menu import Menu, MenuItem, MenuModule


def _sidebar_of(app_config):
    module_name = f"{app_config.name}.sidebar"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return []
        raise
    return [c for c in (getattr(module, "ALL", None) or []) if isinstance(c, dict)]


def _plan(configs):
    """Plain description of the rows to create: [(menu_dict, [item_dict, ...]), ...]."""
    plan = []
    for order, config in enumerate(configs):
        label = config.get("MENU")
        if not label:
            continue
        submenus = config.get("SUBMENUS") or []
        if not submenus:
            if not config.get("ROUTE"):
                continue
            # a direct top-level link: a menu flagged is_direct_link, one page item
            items = [_leaf_dict(config, parent=None)]
            plan.append(({"label": label, "icon": config.get("ICON") or "menu", "order": order,
                          "direct": True}, items))
            continue
        items = [_node_dict(node) for node in submenus if isinstance(node, dict)]
        plan.append(({"label": label, "icon": config.get("ICON") or "menu", "order": order,
                      "direct": False}, items))
    return plan


def _leaf_dict(node, parent):
    return {
        "kind": "page",
        "label": node.get("menu") or node.get("MENU") or "",
        "icon": node.get("icon") or node.get("ICON") or "",
        "route": node.get("route") or node.get("ROUTE") or "",
        "permission": node.get("role") or node.get("ROLE") or "",
        "add_route": node.get("add_route") or "",
        "add_permission": node.get("add_role") or "",
        "children": [],
    }


def _node_dict(node):
    if node.get("submenu"):
        return {
            "kind": "group",
            "label": node.get("menu") or "",
            "icon": node.get("icon") or "",
            "route": "",
            # a group is not gated by its own role: legacy shows it when a child
            # is visible (core/menus.py::filter_menu_by_permission), so it has no code
            "permission": "",
            "add_route": "",
            "add_permission": "",
            "children": [_node_dict(child) for child in node["submenu"] if isinstance(child, dict)],
        }
    return _leaf_dict(node, parent=None)


class Command(BaseCommand):
    help = "Copy the sidebar.py menus into the database (idempotent; dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the rows (default: dry run).")

    def handle(self, *args, **options):
        apply = options["apply"]
        counts = {"menus": 0, "items": 0, "existing_menus": 0, "existing_items": 0}
        with transaction.atomic():
            for app_config in apps.get_app_configs():
                configs = _sidebar_of(app_config)
                if not configs:
                    continue
                for menu_dict, items in _plan(configs):
                    code = f"sidebar.{app_config.label}.{menu_dict['order']}"
                    self._write_menu(app_config, code, menu_dict, items, apply, counts)
            if not apply:
                transaction.set_rollback(True)
        verb = "would create" if not apply else "created"
        self.stdout.write(
            f"{verb}: {counts['menus']} menu(s), {counts['items']} item(s); "
            f"already present: {counts['existing_menus']} menu(s), {counts['existing_items']} item(s)."
        )

    def _write_menu(self, app_config, code, menu_dict, items, apply, counts):
        menu = Menu.objects.filter(code=code).first()
        if menu is None:
            counts["menus"] += 1
            if apply:
                menu = Menu.objects.create(code=code, name=code, label=menu_dict["label"],
                                           icon=menu_dict["icon"], order=menu_dict["order"], is_system=True,
                                           is_direct_link=menu_dict["direct"])
                MenuModule.objects.get_or_create(menu=menu, app=self._app(app_config))
        else:
            counts["existing_menus"] += 1
        for position, item in enumerate(items):
            self._write_item(menu, None, item, position, apply, counts)

    def _write_item(self, menu, parent, item, position, apply, counts):
        existing = None
        if menu is not None and menu.pk:
            existing = MenuItem.objects.filter(
                menu=menu, parent=parent, label=item["label"], route_name=item["route"],
                item_type=self._item_type(item["kind"]),
            ).first()
        if existing is not None:
            counts["existing_items"] += 1
            parent_for_children = existing
        else:
            counts["items"] += 1
            parent_for_children = None
            if apply and menu is not None:
                parent_for_children = MenuItem.objects.create(
                    menu=menu, parent=parent, label=item["label"], icon=item["icon"], order=position,
                    item_type=self._item_type(item["kind"]), route_name=item["route"],
                    permission_code=item["permission"], add_route_name=item["add_route"],
                    add_permission_code=item["add_permission"],
                )
        for child_position, child in enumerate(item["children"]):
            self._write_item(menu, parent_for_children, child, child_position, apply, counts)

    @staticmethod
    def _item_type(kind):
        return {"group": MenuItem.GROUP, "page": MenuItem.PAGE}[kind]

    @staticmethod
    def _app(app_config):
        app, _ = App.objects.get_or_create(name=app_config.label, defaults={"state": "Active"})
        return app
