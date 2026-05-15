
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
                **self.context,
                "include_fields": ["perfil"], # 👈 escolhe aqui
                "exclude_fields": ["user_permissions", "groups", "created_by", "updated_by", "created_by_id", "updated_by_id"]
            }).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["perfil"] = UserSerializer(instance.user, context={
                **self.context,
                "include_fields": ["perfil"], # 👈 escolhe aqui
                "exclude_fields": ["user_permissions", "groups", "created_by", "updated_by", "created_by_id", "updated_by_id"]
            }).data if instance.user else None
        return data


