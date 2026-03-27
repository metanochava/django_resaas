
# =========================
# Django REST Framework
# =========================
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from django_resaas.models.pessoa import Pessoa

from django_resaas.data.pessoa.serializers.pessoa import PessoaSerializer

class  PessoaAPIView(viewsets.ModelViewSet):

    filter_backends = (filters.SearchFilter,)
    
    serializer_class = PessoaSerializer
    queryset = Pessoa.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter().order_by('-id')