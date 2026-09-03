# hr/serializers/contract.py

from rest_framework import serializers
from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.contract import Contract
from django_resaas.hr.models.employee import Employee

from django_resaas.hr.serializers.employee import EmployeeSerializer


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
