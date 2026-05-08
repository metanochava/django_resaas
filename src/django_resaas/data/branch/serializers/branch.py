
from rest_framework import serializers


from django_resaas.models.branch import Branch
from django_resaas.core.base.serializers import BaseSerializer


class BranchSerializer(BaseSerializer):
    class Meta:
        model = Branch
        fields = "__all__"
