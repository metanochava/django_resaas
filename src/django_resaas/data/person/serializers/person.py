
from rest_framework import serializers


from django_resaas.models.person import Person
from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.data.user.serializers.user import UserSerializer

class PersonSerializer(BaseSerializer):
    user_data = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = "__all__"

    def get_user_data(self, obj):
        if not obj.user:
            return None

        return UserSerializer(obj.user)
