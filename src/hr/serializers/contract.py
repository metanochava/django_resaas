# hr/serializers/contract.py

from rest_framework import serializers
from django_resaas.core.base.serializers import BaseSerializer

from hr.models.contract import Contract
from hr.models.employee import Employee

from hr.serializers.employee import EmployeeSerializer


class ContractSerializer(BaseSerializer):

    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        write_only=True
    )

    employee_data = EmployeeSerializer(
        source='employee',
        read_only=True
    )

    class Meta:
        model = Contract
        fields = "__all__"
