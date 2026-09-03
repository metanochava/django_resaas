
from rest_framework import viewsets
from django_resaas.engine.models.branch_user import BranchUser
from django_resaas.engine.data.branch_user.serializers.branch_user import BranchUserSerializer


class  BranchUserAPIView(viewsets.ModelViewSet):
    serializer_class = BranchUserSerializer
    queryset = BranchUser.objects.all()
    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

   