
from rest_framework import serializers


from django_resaas.saas.models.branch_user_group import BranchUserGroup
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
