# hr/views/employee_salary.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.employee_salary import EmployeeSalary
from hr.serializers.employee_salary import EmployeeSalarySerializer


@registerView('employeesalaries')
class EmployeeSalaryAPIView(BaseAPIView):
    queryset = EmployeeSalary.objects.all()
    serializer_class = EmployeeSalarySerializer