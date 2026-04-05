
from rest_framework import serializers


from django_resaas.models.sucursal_user import SucursalUser


class SucursalUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SucursalUser
        fields = "__all__"
