from django_resaas.engine.core.base.serializers import BaseSerializer
from django_resaas.engine.models.user import User
from django_resaas.engine.models.language import Language

from rest_framework import serializers


class MeSerializer(BaseSerializer):

    language = serializers.SerializerMethodField()

    def get_language(self, obj):

        language = getattr(
            obj,
            "language",
            None
        )

        if not language:

            language = Language.objects.filter(
                code="pt-pt"
            ).first()

        if not language:
            return None

        return {
            "id": language.id,
            "name": language.name,
            "code": language.code,
        }

    class Meta:

        model = User

        fields = [
            "id",
            "email",
            "username",
            "profile",
            "mobile",
            "language",
            "last_login",
        ]