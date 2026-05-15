
from rest_framework import serializers


from django_resaas.models.person import Person
from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.data.user.serializers.user import UserSerializer
 
class PersonSerializer(BaseSerializer):
    user_data = UserSerializer(source='user', read_only=True)
    me = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = "__all__" 

    def get_me(self, obj):
        if not obj.user:
            return None
        return UserSerializer(obj.user,
            context={
                "include_fields": ["perfil", "email"]  # 👈 escolhe aqui
            }).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["perfil"] = UserSerializer(instance.user).data if instance.user else None
        return data


