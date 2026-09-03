"""
Changing an already-authenticated user's email or mobile requires proving
ownership of the NEW value via OTP first - `UserSerializer` makes both
fields read-only (see serializers/user.py) specifically so this is the
only path that can ever change them, server-side, not just hidden behind
a nicer frontend flow. Mirrors the registration OTP flow
(views/register_otp.py) but operates on `request.user` instead of
creating a new one, and requires authentication.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_resaas.engine.core.services.otp_service import (
    send_registration_otp,
    verify_registration_otp,
)
from django_resaas.engine.core.utils.translate import Translate
from django_resaas.engine.data.user.serializers.user import UserSerializer
from django_resaas.engine.models.user import User
from django_resaas.notifications.exceptions import NotificationError

_CHANNELS = ("email", "mobile")
_PURPOSE = {"email": "email_change", "mobile": "mobile_change"}


def _validate_channel_and_identifier(request):
    channel = request.data.get("channel")
    identifier = request.data.get("identifier")

    if channel not in _CHANNELS or not identifier:
        return None, None, Response(
            {
                "alert_error": Translate.tdc(
                    request, "channel must be 'email' or 'mobile', with an identifier"
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    taken = (
        User.objects.filter(email=identifier)
        if channel == "email"
        else User.objects.filter(mobile=identifier)
    ).exclude(id=request.user.id).exists()

    if taken:
        return None, None, Response(
            {
                "alert_error": Translate.tdc(
                    request, "This email or phone number is already in use"
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return channel, identifier, None


class RequestProfileContactOTPView(generics.GenericAPIView):
    """Step 1: send an OTP to the NEW email/mobile the user wants to
    switch to (not their current one - it's the new value that needs
    proving)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        channel, identifier, error = _validate_channel_and_identifier(request)
        if error:
            return error

        try:
            send_registration_otp(
                channel, identifier, request=request, purpose=_PURPOSE[channel]
            )
        except NotificationError:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request, "Error sending the verification code"
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"alert_success": Translate.tdc(request, "Verification code sent")},
            status=status.HTTP_200_OK,
        )


class ConfirmProfileContactOTPView(generics.GenericAPIView):
    """Step 2: verify the OTP and only then actually change
    request.user.email/mobile - never before this point."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        channel, identifier, error = _validate_channel_and_identifier(request)
        if error:
            return error

        otp = request.data.get("otp")

        if not verify_registration_otp(channel, identifier, otp):
            return Response(
                {"alert_error": Translate.tdc(request, "Invalid or expired code")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        if channel == "email":
            user.email = identifier
            user.is_verified_email = True
            user.save(update_fields=["email", "is_verified_email"])
        else:
            user.mobile = identifier
            user.is_verified_mobile = True
            user.save(update_fields=["mobile", "is_verified_mobile"])

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
