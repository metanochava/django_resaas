from rest_framework import serializers
from django_resaas.models.modulo import Modulo
from django_resaas.core.base.serializers import BaseSerializer


class ModuloSerializer(BaseSerializer):

    class Meta:
        model = Modulo
        fields = ['id', 'nome']