from django_resaas.saas.core.base.access import ActionPermissionMixin, ExplicitAccessMixin
from rest_framework import viewsets
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.data.branch_user.serializers.branch_user import BranchUserSerializer


class BranchUserAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED: authenticated + signed tenant context + permission per action
    # (ActionPermissionMixin, fail closed) + object scope (get_queryset) +
    # relation validation (BranchUserSerializer.validate).
    #
    # A BranchUser row is what lets a user select a Branch in the signed
    # context (core/tenant/context.py), so it is scoped like
    # BranchUserGroupAPIView: current Entity + current Branch only.

    serializer_class = BranchUserSerializer
    queryset = BranchUser.objects.all()

    action_permissions = {
        "list": "list_branchuser",
        "retrieve": "view_branchuser",
        "create": "add_branchuser",
        "update": "change_branchuser",
        "partial_update": "change_branchuser",
        "destroy": "delete_branchuser",
    }

    def get_queryset(self):
        entity_id = getattr(self.request, "entity_id", None)
        branch_id = getattr(self.request, "branch_id", None)

        if not entity_id or not branch_id:
            return self.queryset.none()

        return self.queryset.filter(
            branch_id=branch_id,
            branch__entity_id=entity_id,
        ).order_by('-id')

    def perform_create(self, serializer):
        # `branch` is read-only (BaseSerializer.DEFAULT_READ_ONLY_FIELDS): it
        # comes from the signed context, never from the body
        serializer.save(branch_id=self.request.branch_id)
