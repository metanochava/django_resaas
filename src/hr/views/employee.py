# hr/views/employee.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.employee import Employee
from hr.serializers.employee import EmployeeSerializer


@registerView('employees')
class EmployeeAPIView(BaseAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer