# hr/views/leave_type.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.leave_type import LeaveType
from django_resaas.hr.serializers.leave_type import LeaveTypeSerializer


@registerView('leavetypes', module='hr')
class LeaveTypeAPIView(BaseAPIView):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
