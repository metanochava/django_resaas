from django.db.models import Q

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from django_saas.models.user import User
from django_saas.core.utils.translate import Translate
from django.utils import timezone


def authenticate(value=None, password=None):
    try:
        user = User.objects.get(
            Q(email=value) |
            Q(username=value) |
            Q(mobile=value)
        )
    except User.DoesNotExist:
        return None

    if user.check_password(password):
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        return user

    return None

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    username = serializers.CharField(read_only=True)
    mobile = serializers.CharField(read_only=True, allow_null=True)
    tokens = serializers.SerializerMethodField(read_only=True)

    def get_tokens(self, obj):
        return obj["tokens"]

    def validate(self, attrs):
        request = self.context.get("request")

        identifier = attrs.get("identifier", "").strip()
        password = attrs.get("password")

        user = authenticate(
            value=identifier,
            password=password,
        )

        if not user:
            raise AuthenticationFailed(
                Translate.tdc(request, "Credenciais inválidas")
            )

        if not user.is_active:
            raise AuthenticationFailed(
                Translate.tdc(request, "Conta desactivada")
            )

        if not user.is_verified_email:
            raise AuthenticationFailed(
                Translate.tdc(request, "Email não verificado")
            )

        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "mobile": user.mobile,
            "tokens": user.tokens(),
        }
