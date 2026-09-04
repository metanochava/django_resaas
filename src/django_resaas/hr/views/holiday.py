# hr/views/holiday.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.holiday import Holiday
from django_resaas.hr.serializers.holiday import HolidaySerializer


@registerView('holidays', module='hr')
class HolidayAPIView(BaseAPIView):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
