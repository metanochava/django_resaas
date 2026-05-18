# hr/views/payslip.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.payslip import Payslip
from hr.serializers.payslip import PayslipSerializer


@registerView('payslips')
class PayslipAPIView(BaseAPIView):
    queryset = Payslip.objects.all()
    serializer_class = PayslipSerializer