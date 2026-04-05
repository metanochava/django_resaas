
from rest_framework import serializers


from django_resaas.models.sucursal_user_group import SucursalUserGroup


class SucursalUserGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SucursalUserGroup
        fields = "__all__"
