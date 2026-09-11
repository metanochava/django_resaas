
from rest_framework import serializers


from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.core.base.serializers import BaseSerializer

class BranchUserSerializer(BaseSerializer):
    class Meta:
        model = BranchUser
        fields = "__all__"
