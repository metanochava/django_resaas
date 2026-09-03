# hr/serializers/payroll_item.py

from rest_framework import serializers
from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.payroll_item import PayrollItem
from django_resaas.hr.models.payroll import Payroll
from django_resaas.hr.models.salary_component import SalaryComponent

from django_resaas.hr.serializers.payroll import PayrollSerializer
from django_resaas.hr.serializers.salary_component import SalaryComponentSerializer


class PayrollItemSerializer(BaseSerializer):

    payroll = serializers.PrimaryKeyRelatedField(
        queryset=Payroll.objects.all(),
        write_only=True
    )

    payroll_data = PayrollSerializer(
        source='payroll',
        read_only=True
    )

    component = serializers.PrimaryKeyRelatedField(
        queryset=SalaryComponent.objects.all(),
        write_only=True
    )

    component_data = SalaryComponentSerializer(
        source='component',
        read_only=True
    )

    class Meta:
        model = PayrollItem
        fields = "__all__"