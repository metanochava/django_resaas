
from rest_framework import serializers


from django_resaas.models.person import Person
from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.data.user.serializers.user import UserSerializer
 
class PersonSerializer(BaseSerializer):
    # user_data = UserSerializer(source='user', read_only=True) # nao descomentar
    profile = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = "__all__" 

    def get_profile(self, obj):
        if not obj.user:
            return None

        data = UserSerializer(obj.user,
            context={  **self.context, "include_fields": ["profile"], # 👈 escolhe aqui
        }).data
        return data['profile']

    # def to_representation(self, instance):
    #     data = super().to_representation(instance)

    #     valor = UserSerializer(instance.user, context={
    #             **self.context,
    #             "include_fields": ["profile"], # 👈 escolhe aqui
    #         }).data if instance.user else None

    #     data["profile"] = valor['profile']
    #     return data


