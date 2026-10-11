from rest_framework import generics, status, permissions
from rest_framework.response import Response

from django_resaas.saas.core.alerts import add_alert
from django_resaas.saas.core.exceptions import error_response
from django_resaas.saas.core.services.otp_service import send_registration_otp
from django_resaas.notifications.exceptions import NotificationError
from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin
from django_resaas.saas.data.user.serializers.register import identifier_is_registered, normalize_identifier
from django_resaas.saas.data.user.views.registration_throttles import (
    RegisterOTPIdentifierThrottle, RegisterOTPThrottle,
)

_CHANNELS = ("email", "mobile")


class RequestRegisterOTPView(ResaasResponseMixin, generics.GenericAPIView):
    """Step 1 of registration: send an OTP to an email or mobile. No auth
    required - the account doesn't exist yet.

    The answer is the same whether or not the address is already registered
    (no code is sent then): this endpoint must not tell anyone which addresses
    have an account. Registration (step 2) says it, only after the code -
    proof of owning the address - was given."""

    # PUBLIC (explicit): used before there is a session
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (RegisterOTPThrottle, RegisterOTPIdentifierThrottle)

    def post(self, request):
        channel = request.data.get("channel")
        identifier = normalize_identifier(channel, request.data.get("identifier"))

        if channel not in _CHANNELS or not identifier:
            return error_response(
                request,
                "channel must be 'email' or 'mobile', with an identifier",
                status.HTTP_400_BAD_REQUEST,
                code="invalid_identifier",
            )

        if not identifier_is_registered(channel, identifier):
            try:
                send_registration_otp(channel, identifier, request=request)
            except NotificationError:
                return error_response(
                    request,
                    "Error sending the verification code",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    code="otp_delivery_failed",
                )

        add_alert(request, "If this email or phone number can be used, a verification code was sent", level="success")
        return Response({"sent": True}, status=status.HTTP_200_OK)
