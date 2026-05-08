from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.user import User
from rest_framework import serializers
from django_resaas.models.language import Language


class MeSerializer(BaseSerializer):
    language = serializers.SerializerMethodField()

    def get_language(self, obj):
        if not obj.language:
            language = Language.objects.filter(code="pt-pt").first()
            return {
                "id": language.id,
                "name": language.name,
                "code": language.code,
            }

        return {
            "id": obj.language.id,
            "name": obj.language.name,
            "code": obj.language.code,
        }

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'perfil', 'mobile', 'language', 'last_login']
