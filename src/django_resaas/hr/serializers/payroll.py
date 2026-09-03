# hr/serializers/payroll.py

from rest_framework import serializers
from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.payroll import Payroll
from django_resaas.hr.models.employee import Employee
from django_resaas.hr.models.payroll_period import PayrollPeriod

from django_resaas.hr.serializers.employee import EmployeeSerializer
from django_resaas.hr.serializers.payroll_period import PayrollPeriodSerializer


class PayrollSerializer(BaseSerializer):

    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        write_only=True
    )

    employee_data = EmployeeSerializer(
        source='employee',
        read_only=True
    )

    period = serializers.PrimaryKeyRelatedField(
        queryset=PayrollPeriod.objects.all(),
        write_only=True
    )

    period_data = PayrollPeriodSerializer(
        source='period',
        read_only=True
    )

    class Meta:
        model = Payroll
        fields = "__all__"