# hr/views/contract.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.contract import Contract
from django_resaas.hr.serializers.contract import ContractSerializer


@registerView('contracts', module='hr')
class ContractAPIView(BaseAPIView):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
