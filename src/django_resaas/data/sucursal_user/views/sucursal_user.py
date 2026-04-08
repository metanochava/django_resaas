
from rest_framework import viewsets
from django_resaas.models.sucursal_user import SucursalUser
from django_resaas.data.sucursal_user.serializers.sucursal_user import SucursalUserSerializer

from django_resaas.core.base.serializers import BaseSerializer
class  SucursalUserAPIView(BaseSerializer):
    serializer_class = SucursalUserSerializer
    queryset = SucursalUser.objects.all()
    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

   