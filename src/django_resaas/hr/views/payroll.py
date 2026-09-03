# hr/views/payroll.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.payroll import Payroll
from django_resaas.hr.serializers.payroll import PayrollSerializer


@registerView('payrolls', module='hr')
class PayrollAPIView(BaseAPIView):
    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer