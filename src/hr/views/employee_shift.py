# hr/views/employee_shift.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.employee_shift import EmployeeShift
from hr.serializers.employee_shift import EmployeeShiftSerializer


@registerView('employeeshifts')
class EmployeeShiftAPIView(BaseAPIView):
    queryset = EmployeeShift.objects.all()
    serializer_class = EmployeeShiftSerializer