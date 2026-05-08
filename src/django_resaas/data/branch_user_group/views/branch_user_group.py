
from rest_framework import viewsets
from django_resaas.models.branch_user_group import BranchUserGroup
from django_resaas.data.branch_user_group.serializers.branch_user_group import BranchUserGroupSerializer


class  BranchUserGroupAPIView(viewsets.ModelViewSet):
    serializer_class = BranchUserGroupSerializer
    queryset = BranchUserGroup.objects.all()

    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

   