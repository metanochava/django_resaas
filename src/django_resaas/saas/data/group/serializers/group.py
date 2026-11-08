from rest_framework import serializers

from django_resaas.saas.models.group import Group
from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.core.menus import menu_roles

class GroupSerializer(BaseSerializer):
    # the codenames the sidebars use as menu entries (same for every group):
    # the Permissions modal shows a menu toggle only for these
    menu_permissions = serializers.SerializerMethodField()

    def get_menu_permissions(self, obj):
        return sorted(menu_roles())

    class Meta:
        model = Group
        fields = ['id', 'name', 'editable', 'hidden_menu_apps', 'hidden_menu_permissions', 'menu_permissions']
        # server-controlled: it decides whether an Entity may change the
        # group's permissions (PermissionAPIView._check_group_scope), so a
        # client can never set it
        read_only_fields = ['editable', 'hidden_menu_apps', 'hidden_menu_permissions']
