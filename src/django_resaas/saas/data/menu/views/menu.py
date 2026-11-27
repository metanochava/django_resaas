"""Menu Manager API (phase 13): the database menus, for the platform administrator.

Platform administration like the App catalogue (data/app/views/app.py): every
action needs its permission (fail closed) and only the Root group holds them -
the codenames are created by the post_migrate signal (core/signals/permissions.py)
for the django_resaas models and Root gets them there; no other group does.

Resources: CRUD on menus and items. Two read-only actions help the editor:
`validate` (MenuValidator) and `resources` (ResourceRegistry). Nothing here
grants access to an endpoint: menus are presentation only.
"""
from dataclasses import asdict

from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django_resaas.saas.core.base.access import ActionPermissionMixin, ExplicitAccessMixin
from django_resaas.saas.core.exceptions import ConflictError
from django_resaas.saas.core.services.menu_validator import MenuValidator
from django_resaas.saas.core.services.resource_registry import ResourceRegistry
from django_resaas.saas.data.menu.serializers.menu import MenuItemSerializer, MenuSerializer
from django_resaas.saas.models.menu import Menu, MenuItem

MENU_PERMISSIONS = {
    "list": "list_menu",
    "retrieve": "view_menu",
    "create": "add_menu",
    "update": "change_menu",
    "partial_update": "change_menu",
    "destroy": "delete_menu",
    "validate_menus": "view_menu",
    "resources": "view_menu",
}

MENU_ITEM_PERMISSIONS = {
    "list": "list_menuitem",
    "retrieve": "view_menuitem",
    "create": "add_menuitem",
    "update": "change_menuitem",
    "partial_update": "change_menuitem",
    "destroy": "delete_menuitem",
}


class MenuAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    action_permissions = MENU_PERMISSIONS
    serializer_class = MenuSerializer
    queryset = Menu.objects.all()
    lookup_field = "id"
    search_fields = ["code", "name", "label"]
    filter_backends = (filters.SearchFilter,)

    def perform_destroy(self, instance):
        # framework menus (is_system) are not deleted from the Menu Manager
        if instance.is_system:
            raise ConflictError("A framework menu cannot be deleted.", code="system_menu")
        instance.delete(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="validate")
    def validate_menus(self, request, *args, **kwargs):
        issues = [asdict(issue) for issue in MenuValidator.validate()]
        return Response(issues)

    @action(detail=False, methods=["get"], url_path="resources")
    def resources(self, request, *args, **kwargs):
        return Response([
            {
                "key": info.key,
                "label": info.label,
                "module": info.module,
                "routes": info.routes,
                "permissions": info.permissions,
                "endpoints": info.endpoints,
            }
            for info in ResourceRegistry.resources()
        ])


class MenuItemAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    action_permissions = MENU_ITEM_PERMISSIONS
    serializer_class = MenuItemSerializer
    queryset = MenuItem.objects.select_related("menu", "parent", "content_type").all()
    lookup_field = "id"
    filter_backends = (filters.SearchFilter,)
    search_fields = ["label", "route_name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        menu = self.request.query_params.get("menu")
        if menu:
            queryset = queryset.filter(menu_id=menu)
        return queryset
