# hr/serializers/payroll_period.py

from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.payroll_period import PayrollPeriod


class PayrollPeriodSerializer(BaseSerializer):

    class Meta:
        model = PayrollPeriod
        fields = "__all__"