
from rest_framework import serializers


from django_resaas.models.branch_user import BranchUser
from django_resaas.core.base.serializers import BaseSerializer

class BranchUserSerializer(BaseSerializer):
    class Meta:
        model = BranchUser
        fields = "__all__"
