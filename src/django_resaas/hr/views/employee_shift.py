# hr/views/employee_shift.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.employee_shift import EmployeeShift
from django_resaas.hr.serializers.employee_shift import EmployeeShiftSerializer


@registerView('employeeshifts', module='hr')
class EmployeeShiftAPIView(BaseAPIView):
    queryset = EmployeeShift.objects.all()
    serializer_class = EmployeeShiftSerializer