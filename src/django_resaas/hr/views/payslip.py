# hr/views/payslip.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.payslip import Payslip
from django_resaas.hr.serializers.payslip import PayslipSerializer


@registerView('payslips', module='hr')
class PayslipAPIView(BaseAPIView):
    queryset = Payslip.objects.all()
    serializer_class = PayslipSerializer