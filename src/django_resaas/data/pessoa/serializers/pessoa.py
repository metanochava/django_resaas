
from rest_framework import serializers


from django_resaas.models.pessoa import Pessoa


class PessoaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pessoa
        fields = "__all__"
