from rest_framework import generics, status
from rest_framework.response import Response

from django_resaas.engine.core.services.otp_service import send_registration_otp
from django_resaas.engine.core.utils.translate import Translate
from django_resaas.engine.models.user import User
from django_resaas.notifications.exceptions import NotificationError

_CHANNELS = ("email", "mobile")


class RequestRegisterOTPView(generics.GenericAPIView):
    """Step 1 of registration: send an OTP to an email or mobile that
    isn't already registered. No auth required - the account doesn't
    exist yet."""

    def post(self, request):
        channel = request.data.get("channel")
        identifier = request.data.get("identifier")

        if channel not in _CHANNELS or not identifier:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request, "channel must be 'email' or 'mobile', with an identifier"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        already_exists = (
            User.objects.filter(email=identifier).exists()
            if channel == "email"
            else User.objects.filter(mobile=identifier).exists()
        )

        if already_exists:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request, "This email or phone number is already registered"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            send_registration_otp(channel, identifier, request=request)
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
            {
                "alert_success": Translate.tdc(
                    request, "Verification code sent"
                )
            },
            status=status.HTTP_200_OK,
        )
