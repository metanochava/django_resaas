from rest_framework import serializers

from django_resaas.models.traducao import Traducao


class TraducaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Traducao
        fields = ['id', 'chave', 'traducao', 'idioma']
