from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import DjangoUnicodeDecodeError, smart_str
from django.utils.http import urlsafe_base64_decode

from rest_framework import serializers

from django_resaas.engine.core.utils.translate import Translate
from django_resaas.engine.models.user import User


class SetNewPasswordSerializer(serializers.Serializer):
    """Completes a password reset: validates the uidb64/token pair the
    user got from their reset-link email, then actually sets the new
    password. Previously this serializer had none of these fields and
    the view never called .save() - the "reset" never really happened."""

    password = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    uidb64 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")

        try:
            user_id = smart_str(urlsafe_base64_decode(attrs["uidb64"]))
            user = User.objects.get(id=user_id)
        except (DjangoUnicodeDecodeError, User.DoesNotExist, ValueError):
            raise serializers.ValidationError(
                Translate.tdc(request, "The reset link is invalid or has expired")
            )

        if not PasswordResetTokenGenerator().check_token(user, attrs["token"]):
            raise serializers.ValidationError(
                Translate.tdc(request, "The reset link is invalid or has expired")
            )

        self._user = user
        return attrs

    def save(self, **kwargs):
        self._user.set_password(self.validated_data["password"])
        self._user.save()
        return self._user
