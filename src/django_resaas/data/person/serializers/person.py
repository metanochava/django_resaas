
from rest_framework import serializers


from django_resaas.models.person import Person
from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.data.user.serializers.user import UserSerializer

class PersonSerializer(BaseSerializer):
    perfil_ = UserSerializer(source='user', read_only=True).data.perfil

    class Meta:
        model = Person
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["perfil"] = UserSerializer(instance.user).data.get("perfil") if instance.user else None
        return data


