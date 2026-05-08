from rest_framework import serializers
from django_resaas.models.app import App
from django_resaas.core.base.serializers import BaseSerializer


class AppSerializer(BaseSerializer):

    class Meta:
        model = App
        fields = ['id', 'name']