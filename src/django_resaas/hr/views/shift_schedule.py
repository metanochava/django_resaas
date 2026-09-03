# hr/views/shift_schedule.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.shift_schedule import ShiftSchedule
from django_resaas.hr.serializers.shift_schedule import ShiftScheduleSerializer


@registerView('shiftschedules', module='hr')
class ShiftScheduleAPIView(BaseAPIView):
    queryset = ShiftSchedule.objects.all()
    serializer_class = ShiftScheduleSerializer