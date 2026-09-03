# hr/serializers/employee_salary.py

from rest_framework import serializers
from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.employee_salary import EmployeeSalary
from django_resaas.hr.models.employee import Employee

from django_resaas.hr.serializers.employee import EmployeeSerializer


class EmployeeSalarySerializer(BaseSerializer):

    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        write_only=True
    )

    employee_data = EmployeeSerializer(
        source='employee',
        read_only=True
    )

    class Meta:
        model = EmployeeSalary
        fields = "__all__"