# hr/views/payroll.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.payroll import Payroll
from hr.serializers.payroll import PayrollSerializer


@registerView('payrolls')
class PayrollAPIView(BaseAPIView):
    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer