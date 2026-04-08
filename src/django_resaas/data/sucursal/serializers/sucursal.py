
from rest_framework import serializers


from django_resaas.models.sucursal import Sucursal
from django_resaas.core.base.serializers import BaseSerializer


class SucursalSerializer(BaseSerializer):
    class Meta:
        model = Sucursal
        fields = "__all_"
