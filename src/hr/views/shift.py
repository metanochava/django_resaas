# hr/views/shift.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.shift import Shift
from hr.serializers.shift import ShiftSerializer


@registerView('shifts')
class ShiftAPIView(BaseAPIView):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer