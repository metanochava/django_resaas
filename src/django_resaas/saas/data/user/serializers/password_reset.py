from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status

from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.core.services.otp_service import (
    clear_failed_otp, otp_attempts_exhausted, otp_scope, record_failed_otp, verify_registration_otp,
)
from django_resaas.saas.core.services.password_reset_service import CHANNELS, METHODS, PURPOSE, find_user, normalize
from django_resaas.saas.core.utils.translate import Translate


class PasswordResetRequestSerializer(serializers.Serializer):
    """password/reset/request/: where to send (channel + identifier) and what
    (method: a link or a code)."""

    channel = serializers.ChoiceField(choices=CHANNELS)
    identifier = serializers.CharField()
    method = serializers.ChoiceField(choices=METHODS, default="link")

    def validate(self, attrs):
        attrs["identifier"] = normalize(attrs["channel"], attrs["identifier"])
        if not attrs["identifier"]:
            raise serializers.ValidationError({"identifier": Translate.tdc(self.context.get("request"), "This field is required.")})
        return attrs


class PasswordResetOTPSerializer(serializers.Serializer):
    """password/reset/otp/complete/: the code sent by password/reset/request/
    (method otp) plus the new password, checked by AUTH_PASSWORD_VALIDATORS.
    At most OTP_MAX_FAILED_ATTEMPTS wrong codes per identifier and window."""

    channel = serializers.ChoiceField(choices=CHANNELS)
    identifier = serializers.CharField()
    otp = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def _tdc(self, text):
        return Translate.tdc(self.context.get("request"), text)

    def validate(self, attrs):
        channel = attrs["channel"]
        identifier = normalize(channel, attrs["identifier"])
        attrs["identifier"] = identifier
        scope = otp_scope(identifier, PURPOSE)

        if otp_attempts_exhausted(scope):
            raise ResaasAPIException(
                "Too many attempts. Request a new code in a few minutes.",
                code="too_many_attempts",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # the same answer for an unknown identifier and a wrong code: this
        # endpoint must not tell which e-mails / numbers have an account
        user = find_user(channel, identifier)
        if user is None or not verify_registration_otp(channel, identifier, attrs["otp"], purpose=PURPOSE):
            record_failed_otp(scope)
            raise serializers.ValidationError({"otp": self._tdc("Invalid or expired verification code")})

        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": [self._tdc(message) for message in error.messages]})

        self._user = user
        return attrs

    def save(self, **kwargs):
        user = self._user
        user.set_password(self.validated_data["password"])
        fields = ["password"]
        # receiving the code proved the address belongs to this user
        flag = "is_verified_email" if self.validated_data["channel"] == "email" else "is_verified_mobile"
        setattr(user, flag, True)
        fields.append(flag)
        user.save(update_fields=fields)
        clear_failed_otp(otp_scope(self.validated_data["identifier"], PURPOSE))
        return user
