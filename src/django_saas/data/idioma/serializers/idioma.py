from rest_framework import serializers

from django_saas.models.idioma import Idioma


class IdiomaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Idioma
        fields = ['id', 'nome', 'code', 'estado']
