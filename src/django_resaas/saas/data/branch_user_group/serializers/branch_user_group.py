
from rest_framework import serializers


from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.core.base.serializers import BaseSerializer


class BranchUserGroupSerializer(BaseSerializer):
    # BaseSerializer.DEFAULT_READ_ONLY_FIELDS forces "branch" read-only,
    # assuming the BaseModel auto-tenant field (populated from request
    # context by BaseAPIView.perform_create). BranchUserGroup is a
    # TimeModel, not a BaseModel - its `branch` is real, user-supplied
    # domain data (which branch this user/group binding applies to),
    # and BranchUserGroupAPIView is a plain ModelViewSet with no such
    # auto-injection, so forcing it read-only made every create() fail
    # with a NOT NULL branch_id error.
    DEFAULT_READ_ONLY_FIELDS = tuple(
        f for f in BaseSerializer.DEFAULT_READ_ONLY_FIELDS if f != "branch"
    )

    class Meta:
        model = BranchUserGroup
        fields = "__all__"

    def validate(self, attrs):
        # TenantRelationsMixin already refuses a branch of another Entity.
        # User and Group carry no `entity`, so the generic check cannot see
        # them: an assignment is a permission grant, so here the relations
        # must belong to the signed context - the same rules as
        # UserAPIView.addGroup (current branch, a Group the Entity owns, a
        # member of the Entity). Partial updates are checked against the
        # resulting row, not only the fields sent.
        attrs = super().validate(attrs)

        request = self.context.get("request")
        entity_id = getattr(request, "entity_id", None)
        branch_id = getattr(request, "branch_id", None)

        if not entity_id or not branch_id:
            return attrs

        def resulting(name):
            if name in attrs:
                return attrs[name]
            return getattr(self.instance, name, None)

        branch, user, group = resulting("branch"), resulting("user"), resulting("group")
        errors = {}

        if branch is not None and str(branch.id) != str(branch_id):
            errors["branch"] = "This assignment must use the current branch."

        if group is not None and not EntityGroup.objects.filter(entity_id=entity_id, group_id=group.id).exists():
            errors["group"] = "This profile does not belong to the current entity."

        if user is not None and not EntityUser.objects.filter(entity_id=entity_id, user_id=user.id).exists():
            errors["user"] = "This user is not a member of the current entity."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs
