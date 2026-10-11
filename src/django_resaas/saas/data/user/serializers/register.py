from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers, status

from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.core.services.otp_service import (
    clear_failed_otp, otp_attempts_exhausted, record_failed_otp, verify_registration_otp,
)
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.core.utils.username import (
    USERNAME_MAX_LENGTH, USERNAME_MIN_LENGTH, normalize_username, username_is_taken, username_is_valid,
)
from django_resaas.saas.models.user import User


def normalize_identifier(channel, identifier):
    """The stored form of an e-mail / mobile: trimmed; e-mails lowercase, mobiles
    without spaces. Same rule for the code request and the registration."""
    value = str(identifier or "").strip()
    if channel == "email":
        return value.lower()
    return value.replace(" ", "")


def identifier_is_registered(channel, identifier):
    if channel == "email":
        return User.objects.filter(email__iexact=identifier).exists()
    return User.objects.filter(mobile=identifier).exists()


class RegisterSerializer(serializers.Serializer):
    """Step 2 of registration: complete account creation with the OTP
    obtained from RequestRegisterOTPView. Creates the User only - never an
    Entity, Branch or profile membership (access is granted separately, by an
    authorised operation)."""

    name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    channel = serializers.ChoiceField(choices=("email", "mobile"))
    identifier = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True)

    def _tdc(self, text):
        return Translate.tdc(self.context.get("request"), text)

    def validate_username(self, value):
        value = normalize_username(value)

        if not username_is_valid(value):
            raise serializers.ValidationError(self._tdc(
                "Use {min} to {max} lowercase letters, digits, dots or underscores, starting with a letter"
            ).replace("{min}", str(USERNAME_MIN_LENGTH)).replace("{max}", str(USERNAME_MAX_LENGTH)))

        if username_is_taken(value):
            raise serializers.ValidationError(self._tdc("This username is already taken"))

        return value

    def validate(self, attrs):
        channel = attrs["channel"]
        identifier = normalize_identifier(channel, attrs["identifier"])
        attrs["identifier"] = identifier

        # the code first: until it is proven, nothing about the identifier is said
        if otp_attempts_exhausted(identifier):
            raise ResaasAPIException(
                "Too many attempts. Request a new code in a few minutes.",
                code="too_many_attempts",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not verify_registration_otp(channel, identifier, attrs["otp"]):
            record_failed_otp(identifier)
            raise serializers.ValidationError({"otp": self._tdc("Invalid or expired verification code")})

        if identifier_is_registered(channel, identifier):
            raise serializers.ValidationError({"identifier": self._tdc("This email or phone number is already registered")})

        candidate = User(
            username=attrs["username"],
            email=identifier if channel == "email" else None,
            mobile=identifier if channel == "mobile" else None,
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": [self._tdc(message) for message in error.messages]})

        return attrs

    def create(self, validated_data):
        channel = validated_data["channel"]
        identifier = validated_data["identifier"]
        words = str(validated_data.get("name") or "").split()

        user = User(
            username=validated_data["username"],
            email=identifier if channel == "email" else None,
            mobile=identifier if channel == "mobile" else None,
            # the Person auto-created for this User takes its name from these
            first_name=words[0] if words else None,
            last_name=" ".join(words[1:]) or None,
        )
        user.set_password(validated_data["password"])
        if channel == "email":
            user.is_verified_email = True
        else:
            user.is_verified_mobile = True

        try:
            with transaction.atomic():
                user.save()
        except IntegrityError:
            # a concurrent registration took the username or the identifier
            # between validation and save: the UNIQUE constraints decided
            if username_is_taken(user.username):
                raise serializers.ValidationError({"username": self._tdc("This username is already taken")})
            raise serializers.ValidationError({"identifier": self._tdc("This email or phone number is already registered")})

        clear_failed_otp(identifier)
        return user
