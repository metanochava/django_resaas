# hr/views/employee_salary.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.employee_salary import EmployeeSalary
from django_resaas.hr.serializers.employee_salary import EmployeeSalarySerializer


@registerView('employeesalaries', module='hr')
class EmployeeSalaryAPIView(BaseAPIView):
    queryset = EmployeeSalary.objects.all()
    serializer_class = EmployeeSalarySerializer