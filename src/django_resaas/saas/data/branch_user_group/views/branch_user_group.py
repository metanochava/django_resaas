
from rest_framework import viewsets
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.data.branch_user_group.serializers.branch_user_group import BranchUserGroupSerializer


class  BranchUserGroupAPIView(viewsets.ModelViewSet):
    serializer_class = BranchUserGroupSerializer
    queryset = BranchUserGroup.objects.all()

    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

    def perform_create(self, serializer):
        # A tela de Add genérica não expõe "state" como campo editável -
        # sem isto o CharField cai no default do model (TimeModel.state =
        # "Inactive"), criando associações inactivas por omissão.
        if not serializer.validated_data.get("state"):
            serializer.save(state="Active")
        else:
            serializer.save()

   