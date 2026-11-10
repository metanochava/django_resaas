from rest_framework import serializers

from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.branch_opening_hours import BranchOpeningHours


class BranchOpeningHoursSerializer(BaseSerializer):
    # the branch is checked against the current Entity by TenantRelationsMixin

    class Meta:
        model = BranchOpeningHours
        fields = "__all__"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        opens_at = attrs.get("opens_at", getattr(self.instance, "opens_at", None))
        closes_at = attrs.get("closes_at", getattr(self.instance, "closes_at", None))
        if opens_at and closes_at and closes_at <= opens_at:
            raise serializers.ValidationError({"closes_at": "The closing time must be after the opening time."})
        return attrs
