"""MenuRepository: read access to the database menus (MENU_IMPLEMENTATION_PROGRESS.md, phase 6).

Read only, and not used by build_menus yet. It answers three questions with a
fixed number of queries, whatever the size of the configuration:

- which menus are active and presented in the given modules;
- which active items each menu has, grouped by parent (for the tree builder);
- whether one item applies to the given modules.

Module rules (models/menu.py):
- a menu with no MenuModule rows is not restricted to a module;
- an item with no MenuItemModule rows inherits its menu's presentation;
- an item with MenuItemModule rows is shown only in those modules.

Module names are matched against App.name, as core/menus.py active_app_names does.
Permissions are not decided here: visibility by profile is the builder's job.
"""
from django.db.models import Q

from django_resaas.saas.models.menu import Menu, MenuItem, MenuItemModule, MenuModule


class MenuRepository:

    @staticmethod
    def active_menus(app_names=None):
        """Active menus presented in `app_names` (or in any module when None).
        A menu with no module restriction is always included."""
        menus = Menu.objects.filter(state="Active")
        if app_names is not None:
            names = [str(name) for name in app_names]
            menus = menus.filter(
                Q(modules__isnull=True) | Q(modules__app__name__in=names)
            ).distinct()
        return list(menus.order_by("order", "code"))

    @staticmethod
    def module_names_of_menus(menu_ids):
        """{menu_id: {module name, ...}} for these menus, in one query. A menu
        missing from the dict has no module restriction."""
        names = {}
        rows = MenuModule.objects.filter(menu_id__in=list(menu_ids), app__name__isnull=False)
        for menu_id, app_name in rows.values_list("menu_id", "app__name"):
            names.setdefault(menu_id, set()).add(str(app_name))
        return names

    @staticmethod
    def items_by_parent(menu_ids):
        """Active items of these menus in a fixed number of queries, grouped as
        {(menu_id, parent_id): [item, ...]} in display order. Top level items
        have parent_id None. Module restrictions are loaded in one more query for item_applies()."""
        items = (
            MenuItem.objects.filter(menu_id__in=list(menu_ids), state="Active")
            .select_related("content_type")
            .order_by("order", "label")
        )
        items = list(items)
        restrictions = {}
        rows = MenuItemModule.objects.filter(item_id__in=[i.id for i in items], app__name__isnull=False)
        for item_id, app_name in rows.values_list("item_id", "app__name"):
            restrictions.setdefault(item_id, set()).add(str(app_name))
        grouped = {}
        for item in items:
            item._module_names = restrictions.get(item.id, set())
            grouped.setdefault((item.menu_id, item.parent_id), []).append(item)
        return grouped

    @staticmethod
    def item_applies(item, app_names=None):
        """True when the item is presented in `app_names` (None = no module filter).
        With no item restriction it follows its menu, which active_menus() has
        already filtered."""
        if app_names is None:
            return True
        restricted = getattr(item, "_module_names", None)
        if restricted is None:
            restricted = {
                str(name) for name in MenuItemModule.objects.filter(item=item, app__name__isnull=False)
                .values_list("app__name", flat=True)
            }
        if not restricted:
            return True
        return bool(restricted & {str(name) for name in app_names})
