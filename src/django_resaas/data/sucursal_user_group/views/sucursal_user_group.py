
from rest_framework import viewsets
from django_resaas.models.sucursal_user_group import SucursalUserGroup
from django_resaas.data.sucursal_user_group.serializers.sucursal_user_group import SucursalUserGroupSerializer


class  SucursalUserGroupAPIView(viewsets.ModelViewSet):
    serializer_class = SucursalUserGroupSerializer
    queryset = SucursalUserGroup.objects.all()

    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

   