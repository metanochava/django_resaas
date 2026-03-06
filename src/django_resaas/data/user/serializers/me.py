from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.user import User
from rest_framework import serializers
from django_resaas.models.idioma import Idioma


class MeSerializer(BaseSerializer):
    language = serializers.SerializerMethodField()

    def get_language(self, obj):
        if not obj.language:
            idioma = Idioma.objects.filter(code="pt-pt").first()
            return {
                "id": idioma.id,
                "nome": idioma.nome,
                "code": idioma.code,
            }

        return {
            "id": obj.language.id,
            "nome": obj.language.nome,
            "code": obj.language.code,
        }

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'perfil', 'mobile', 'language', 'last_login']
