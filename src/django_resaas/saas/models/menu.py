"""Database-driven navigation menus (MENU_IMPLEMENTATION_PROGRESS.md, phase 3).

Global configuration: no Entity or Branch on these rows (one menu definition is
shared by every tenant; what a profile may see is still decided by its effective
permissions and the module entitlements in core/menus.py).

A menu item may be a GROUP (holds other items), a RESOURCE (points to a model
through ContentType) or a PAGE (a named route: dashboard, report, workflow).
The menu never grants access: `permission_code` only decides visibility, the
API keeps validating each request.
"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models

from django_resaas.saas.core.base.models import TimeModel


class Menu(TimeModel):
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    label = models.CharField(max_length=120)
    icon = models.CharField(max_length=80, blank=True, default="")
    description = models.TextField(blank=True, default="")
    order = models.IntegerField(default=0)
    is_system = models.BooleanField(default=False, help_text="Internal menu of the framework.")
    # a direct top-level link (one page, no submenu): shown as a link, not a group.
    # Its single root item is the page; the menu's label is the link text.
    is_direct_link = models.BooleanField(default=False)

    # a menu is active unless someone deactivates it (TimeModel defaults to Inactive)
    state = models.CharField(
        default="Active",
        choices=(("Inactive", "Inactive"), ("Active", "Active")),
        max_length=20,
    )

    class Meta:
        ordering = ["order", "code"]
        verbose_name = "Menu"
        verbose_name_plural = "Menus"

    def __str__(self):
        return self.label or self.name or self.code


class MenuItem(TimeModel):
    GROUP = "group"
    RESOURCE = "resource"
    PAGE = "page"
    ITEM_TYPE_CHOICES = (
        (GROUP, "Group"),
        (RESOURCE, "Resource"),
        (PAGE, "Page"),
    )

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="items")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    label = models.CharField(max_length=120)
    icon = models.CharField(max_length=80, blank=True, default="")
    order = models.IntegerField(default=0)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default=PAGE)

    # RESOURCE: the model it lists (and its action, e.g. "list")
    content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL, related_name="menu_items"
    )
    resource_action = models.CharField(max_length=60, blank=True, default="")

    # PAGE / RESOURCE: the frontend route name, and the creation route if any
    route_name = models.CharField(max_length=120, blank=True, default="")
    add_route_name = models.CharField(max_length=120, blank=True, default="")

    # visibility only (never a grant): the codename the profile must hold
    permission_code = models.CharField(max_length=120, blank=True, default="")
    add_permission_code = models.CharField(max_length=120, blank=True, default="")

    state = models.CharField(
        default="Active",
        choices=(("Inactive", "Inactive"), ("Active", "Active")),
        max_length=20,
    )

    class Meta:
        ordering = ["order", "label"]
        verbose_name = "Menu item"
        verbose_name_plural = "Menu items"
        indexes = [models.Index(fields=["menu", "parent", "order"])]

    def __str__(self):
        return self.label


class MenuModule(TimeModel):
    """A menu presented in these modules (an App). Empty = not restricted."""

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="modules")
    app = models.ForeignKey("django_resaas.App", on_delete=models.CASCADE, related_name="menu_modules")

    class Meta:
        unique_together = ("menu", "app")
        verbose_name = "Menu module"
        verbose_name_plural = "Menu modules"


class MenuItemModule(TimeModel):
    """Restricts one item to these modules. An item with none inherits its menu's."""

    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="modules")
    app = models.ForeignKey("django_resaas.App", on_delete=models.CASCADE, related_name="menu_item_modules")

    class Meta:
        unique_together = ("item", "app")
        verbose_name = "Menu item module"
        verbose_name_plural = "Menu item modules"
