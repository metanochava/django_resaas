# hr/views/shift_schedule.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.shift_schedule import ShiftSchedule
from hr.serializers.shift_schedule import ShiftScheduleSerializer


@registerView('shiftschedules')
class ShiftScheduleAPIView(BaseAPIView):
    queryset = ShiftSchedule.objects.all()
    serializer_class = ShiftScheduleSerializer