from rest_framework import generics, permissions, status
from rest_framework.response import Response

from django_resaas.notifications.exceptions import NotificationError
from django_resaas.saas.core.alerts import add_alert
from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin
from django_resaas.saas.core.exceptions import error_response
from django_resaas.saas.core.services.password_reset_service import (
    ResetLinkUnavailable, find_user, link_available, send_code, send_link,
)
from django_resaas.saas.data.user.serializers.password_reset import (
    PasswordResetOTPSerializer, PasswordResetRequestSerializer,
)
from django_resaas.saas.data.user.views.registration_throttles import (
    PasswordResetOTPIdentifierThrottle, PasswordResetOTPThrottle, PasswordResetThrottle,
)


class RequestPasswordResetAPIView(ResaasResponseMixin, generics.GenericAPIView):
    """Step 1 of "forgot my password": {channel: email|mobile, identifier,
    method: link|otp}. Sends a reset link or a code to that e-mail / phone.

    The answer is the same whether or not the identifier has an account
    (something is sent only when it has one): this endpoint must not tell
    anyone which e-mails or numbers are registered."""

    # PUBLIC (explicit): used before there is a session
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (PasswordResetOTPThrottle, PasswordResetOTPIdentifierThrottle)
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel = serializer.validated_data["channel"]
        identifier = serializer.validated_data["identifier"]
        method = serializer.validated_data["method"]

        # before the lookup: the answer must not depend on the account existing
        if method == "link" and not link_available(request):
            return self._link_unavailable(request)

        user = find_user(channel, identifier)
        if user is not None:
            try:
                if method == "link":
                    send_link(request, user, channel)
                else:
                    send_code(request, channel, identifier)
            except ResetLinkUnavailable:
                return self._link_unavailable(request)
            except NotificationError:
                return error_response(
                    request,
                    "Error sending the verification code" if method == "otp" else "Error sending the reset link",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    code="reset_delivery_failed",
                )

        add_alert(
            request,
            "If this email or phone number is registered, a reset link was sent"
            if method == "link" else
            "If this email or phone number is registered, a verification code was sent",
            level="success",
        )
        return Response({"sent": True, "method": method}, status=status.HTTP_200_OK)

    @staticmethod
    def _link_unavailable(request):
        return error_response(
            request,
            "The reset link cannot be sent from this address. Ask for a code instead.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
            code="reset_link_unavailable",
        )


class CompletePasswordResetOTPAPIView(ResaasResponseMixin, generics.GenericAPIView):
    """Step 2 with a code: {channel, identifier, otp, password}. 202 on success
    (the POST rule of ResaasResponseMixin); 400 with error.details.otp /
    .password; 429 after too many wrong codes. A link is completed instead by
    PATCH password/reset/complete/ (uidb64 + token)."""

    # PUBLIC (explicit): used before there is a session
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (PasswordResetThrottle,)
    serializer_class = PasswordResetOTPSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        add_alert(request, "Password reset successfully", level="success")
        return Response({"reset": True}, status=status.HTTP_200_OK)
