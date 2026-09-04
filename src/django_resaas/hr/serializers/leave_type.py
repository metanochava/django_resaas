# hr/serializers/leave_type.py

from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.leave_type import LeaveType


class LeaveTypeSerializer(BaseSerializer):

    class Meta:
        model = LeaveType
        fields = "__all__"
