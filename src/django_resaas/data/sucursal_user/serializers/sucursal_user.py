
from rest_framework import serializers


from django_resaas.models.sucursal_user import SucursalUser
from django_resaas.core.base.serializers import BaseSerializer

class SucursalUserSerializer(BaseSerializer):
    class Meta:
        model = SucursalUser
        fields = "__all__"
