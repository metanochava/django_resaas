# hr/views/attendance.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.attendance import Attendance
from hr.serializers.attendance import AttendanceSerializer


@registerView('attendances')
class AttendanceAPIView(BaseAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer