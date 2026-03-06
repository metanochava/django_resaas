from rest_framework import serializers

from django_saas.models.traducao import Traducao


class TraducaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Traducao
        fields = ['id', 'chave', 'traducao', 'idioma']
