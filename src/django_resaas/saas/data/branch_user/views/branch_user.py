
from django_resaas.saas.core.base.access import ExplicitAccessMixin
from rest_framework import viewsets
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.data.branch_user.serializers.branch_user import BranchUserSerializer


class BranchUserAPIView(ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED: authenticated callers only (no public actions)

    serializer_class = BranchUserSerializer
    queryset = BranchUser.objects.all()
    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

   