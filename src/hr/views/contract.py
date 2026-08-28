# hr/views/contract.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.contract import Contract
from hr.serializers.contract import ContractSerializer


@registerView('contracts')
class ContractAPIView(BaseAPIView):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
