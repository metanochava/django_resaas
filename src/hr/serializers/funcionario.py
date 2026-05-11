# rh/api/serializers/employee.py

from django_resaas.core.base.serializers import BaseSerializer
from hr.models.employee import Employee

class EmployeeSerializer(BaseSerializer):
    class Meta:
        model = Employee
        fields = "__all__"