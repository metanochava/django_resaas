# hr/serializers/payslip.py

from rest_framework import serializers
from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.payslip import Payslip
from django_resaas.hr.models.payroll import Payroll

from django_resaas.hr.serializers.payroll import PayrollSerializer


class PayslipSerializer(BaseSerializer):

    payroll = serializers.PrimaryKeyRelatedField(
        queryset=Payroll.objects.all(),
        write_only=True
    )

    payroll_data = PayrollSerializer(
        source='payroll',
        read_only=True
    )

    class Meta:
        model = Payslip
        fields = "__all__"