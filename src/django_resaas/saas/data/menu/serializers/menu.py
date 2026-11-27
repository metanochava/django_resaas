from rest_framework import serializers

from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.menu import Menu, MenuItem


class MenuSerializer(BaseSerializer):

    class Meta:
        model = Menu
        fields = ["id", "code", "name", "label", "icon", "description", "order", "state", "is_system"]
        read_only_fields = ["is_system"]


class MenuItemSerializer(BaseSerializer):

    class Meta:
        model = MenuItem
        fields = [
            "id", "menu", "parent", "label", "icon", "order", "item_type",
            "content_type", "resource_action", "route_name", "add_route_name",
            "permission_code", "add_permission_code", "state",
        ]

    def validate(self, attrs):
        """Structure rules the database cannot express: the parent belongs to the
        same menu, and an item is never its own ancestor (no cycle)."""
        menu = attrs.get("menu", getattr(self.instance, "menu", None))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))

        if parent is not None:
            if menu is not None and parent.menu_id != menu.id:
                raise serializers.ValidationError({"parent": ["The parent item belongs to another menu."]})
            if self.instance is not None:
                node = parent
                while node is not None:
                    if node.id == self.instance.id:
                        raise serializers.ValidationError({"parent": ["An item cannot be its own ancestor."]})
                    node = node.parent

        item_type = attrs.get("item_type", getattr(self.instance, "item_type", MenuItem.PAGE))
        if item_type == MenuItem.PAGE and not attrs.get("route_name", getattr(self.instance, "route_name", "")):
            raise serializers.ValidationError({"route_name": ["A page item needs a route name."]})
        return attrs
