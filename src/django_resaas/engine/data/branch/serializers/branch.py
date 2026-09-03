
from rest_framework import serializers


from django_resaas.engine.models.branch import Branch
from django_resaas.engine.core.base.serializers import BaseSerializer


class BranchSerializer(BaseSerializer):
    class Meta:
        model = Branch
        fields = "__all__"
