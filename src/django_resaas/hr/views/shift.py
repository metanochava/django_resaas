# hr/views/shift.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.shift import Shift
from django_resaas.hr.serializers.shift import ShiftSerializer


@registerView('shifts', module='hr')
class ShiftAPIView(BaseAPIView):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer