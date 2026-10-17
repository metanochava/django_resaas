
from django_resaas.saas.core.base.access import ActionPermissionMixin, ExplicitAccessMixin
from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.core.services import group_access_service
from rest_framework import viewsets
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.data.branch_user_group.serializers.branch_user_group import BranchUserGroupSerializer


class BranchUserGroupAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED: authenticated + signed tenant context + permission per action
    # (ActionPermissionMixin, fail closed) + object scope (get_queryset) +
    # relation validation (BranchUserGroupSerializer.validate).
    #
    # A BranchUserGroup row IS an authorization grant (check_permission reads
    # it), so this endpoint is scoped like UserAPIView.addGroup/removeGroup:
    # current Entity + current Branch, groups the Entity owns, users who are
    # members of it. Cross-branch / cross-entity access is not enabled here.

    serializer_class = BranchUserGroupSerializer
    queryset = BranchUserGroup.objects.all()

    action_permissions = {
        "list": "list_branchusergroup",
        "retrieve": "view_branchusergroup",
        "create": "add_branchusergroup",
        "update": "change_branchusergroup",
        "partial_update": "change_branchusergroup",
        "destroy": "delete_branchusergroup",
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

    def check_self_grant(self, serializer):
        # no self-elevation: giving YOURSELF a profile is a grant of all its
        # permissions, so the same delegation rule as editing a profile's
        # permissions applies (group_access_service.check_delegation:
        # platform level exempt, otherwise 403 permission_not_held)
        data = serializer.validated_data
        user = data.get("user", getattr(serializer.instance, "user", None))
        group = data.get("group", getattr(serializer.instance, "group", None))

        if user is not None and group is not None and str(user.id) == str(self.request.user.id):
            group_access_service.check_delegation(self.request, group.permissions.all())

    def perform_update(self, serializer):
        self.check_self_grant(serializer)
        serializer.save()

    def perform_create(self, serializer):
        self.check_self_grant(serializer)

        # A tela de Add genérica não expõe "state" como campo editável -
        # sem isto o CharField cai no default do model (TimeModel.state =
        # "Inactive"), criando associações inactivas por omissão.
        if not serializer.validated_data.get("state"):
            serializer.save(state="Active")
        else:
            serializer.save()

    def perform_destroy(self, instance):
        # never lock yourself out of the profile you are acting with (same
        # rule as UserAPIView.removeGroup)
        if (
            str(instance.user_id) == str(self.request.user.id)
            and str(instance.group_id) == str(getattr(self.request, "group_id", None))
        ):
            raise ResaasAPIException(
                "You cannot remove the profile you are currently using.",
                code="cannot_remove_own_active_group",
                status_code=400,
            )

        instance.delete()
