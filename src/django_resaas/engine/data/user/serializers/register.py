from rest_framework import serializers

from django_resaas.engine.core.services.otp_service import verify_registration_otp
from django_resaas.engine.core.utils.translate import Translate
from django_resaas.engine.models.user import User


class RegisterSerializer(serializers.Serializer):
    """Step 2 of registration: complete account creation with the OTP
    obtained from RequestRegisterOTPView. Not a ModelSerializer anymore -
    `channel`/`identifier`/`otp` aren't User fields, they're inputs this
    serializer turns into a User itself."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    channel = serializers.ChoiceField(choices=("email", "mobile"))
    identifier = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True)

    def validate_username(self, value):
        request = self.context.get("request")

        if not value.isalnum():
            raise serializers.ValidationError(
                Translate.tdc(
                    request,
                    "The username must contain only alphanumeric characters",
                )
            )

        return value

    def validate(self, attrs):
        request = self.context.get("request")

        if not verify_registration_otp(
            attrs["channel"], attrs["identifier"], attrs["otp"]
        ):
            raise serializers.ValidationError(
                {
                    "otp": Translate.tdc(
                        request, "Invalid or expired verification code"
                    )
                }
            )

        return attrs

    def create(self, validated_data):
        channel = validated_data["channel"]
        identifier = validated_data["identifier"]

        user = User.objects.create_user(
            username=validated_data["username"],
            email=identifier if channel == "email" else None,
            mobile=identifier if channel == "mobile" else None,
            password=validated_data["password"],
        )

        if channel == "email":
            user.is_verified_email = True
        else:
            user.is_verified_mobile = True

        user.save()
        return user
