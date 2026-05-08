
from rest_framework import serializers


from django_resaas.models.person import Person
from django_resaas.core.base.serializers import BaseSerializer

class PersonSerializer(BaseSerializer):
    class Meta:
        model = Person
        fields = "__all__"
