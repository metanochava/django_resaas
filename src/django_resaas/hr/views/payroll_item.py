# hr/views/payroll_item.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.payroll_item import PayrollItem
from django_resaas.hr.serializers.payroll_item import PayrollItemSerializer


@registerView('payrollitems', module='hr')
class PayrollItemAPIView(BaseAPIView):
    queryset = PayrollItem.objects.all()
    serializer_class = PayrollItemSerializer