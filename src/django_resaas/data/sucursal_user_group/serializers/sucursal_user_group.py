
from rest_framework import serializers


from django_resaas.models.sucursal_user_group import SucursalUserGroup
from django_resaas.core.base.serializers import BaseSerializer


class SucursalUserGroupSerializer(BaseSerializer):
    class Meta:
        model = SucursalUserGroup
        fields = "__all__"
