from rest_framework import serializers

from django_resaas.models.idioma import Idioma
from django_resaas.core.base.serializers import BaseSerializer


class IdiomaSerializer(BaseSerializer):
    class Meta:
        model = Idioma
        fields = "__all__"
