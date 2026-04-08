
from rest_framework import serializers


from django_resaas.models.pessoa import Pessoa
from django_resaas.core.base.serializers import BaseSerializer

class PessoaSerializer(BaseSerializer):
    class Meta:
        model = Pessoa
        fields = "__all__"
