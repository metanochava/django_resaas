
from rest_framework import serializers


from django_resaas.engine.models.branch_user_group import BranchUserGroup
from django_resaas.engine.core.base.serializers import BaseSerializer


class BranchUserGroupSerializer(BaseSerializer):
    class Meta:
        model = BranchUserGroup
        fields = "__all__"
