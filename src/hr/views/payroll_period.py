# hr/views/payroll_period.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.payroll_period import PayrollPeriod
from hr.serializers.payroll_period import PayrollPeriodSerializer


@registerView('payrollperiods')
class PayrollPeriodAPIView(BaseAPIView):
    queryset = PayrollPeriod.objects.all()
    serializer_class = PayrollPeriodSerializer