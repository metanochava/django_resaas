# hr/views/payroll_period.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.payroll_period import PayrollPeriod
from django_resaas.hr.serializers.payroll_period import PayrollPeriodSerializer


@registerView('payrollperiods', module='hr')
class PayrollPeriodAPIView(BaseAPIView):
    queryset = PayrollPeriod.objects.all()
    serializer_class = PayrollPeriodSerializer