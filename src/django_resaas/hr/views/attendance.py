# hr/views/attendance.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.attendance import Attendance
from django_resaas.hr.serializers.attendance import AttendanceSerializer


@registerView('attendances', module='hr')
class AttendanceAPIView(BaseAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer