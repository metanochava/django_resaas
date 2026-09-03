# hr/views/employee.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.employee import Employee
from django_resaas.hr.serializers.employee import EmployeeSerializer


@registerView('employees', module='hr')
class EmployeeAPIView(BaseAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer