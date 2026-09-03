from rest_framework import serializers
from django_resaas.engine.models.app import App
from django_resaas.engine.core.base.serializers import BaseSerializer


class AppSerializer(BaseSerializer):

    class Meta:
        model = App
        fields = ['id', 'name']