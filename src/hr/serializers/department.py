# hr/serializers/department.py

from rest_framework import serializers
from django_resaas.core.base.serializers import BaseSerializer

from hr.models.department import Department
from hr.models.employee import Employee

from hr.serializers.employee import EmployeeSerializer


class DepartmentSerializer(BaseSerializer):

    manager = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    manager_data = EmployeeSerializer(source='manager', read_only=True)

    class Meta:
        model = Department
        fields = "__all__"