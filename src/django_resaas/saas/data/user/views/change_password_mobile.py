from rest_framework import status
from rest_framework.response import Response

from django_resaas.saas.core.alerts import add_alert
from django_resaas.saas.data.user.views.password_reset import CompletePasswordResetOTPAPIView


class ChangePasswordMobileAPIView(CompletePasswordResetOTPAPIView):
    """
    POST password/change/mobile/  {mobile, otp, password}   (DEPRECATED - use
    POST password/reset/otp/complete/ {channel: "mobile", identifier, otp, password})

    PUBLIC (explicit): used before there is a session.

    A compatibility alias of password/reset/otp/complete/ with
    channel="mobile": the code is the one sent by password/reset/request/
    (channel "mobile", method "otp"), bound to its purpose, throttled, with an
    attempt limit and the password policy. It used to accept a day-long
    counter HOTP that nothing ever sent and that was never consumed, with no
    attempt limit - i.e. a brute-forceable public password change for any
    account with a phone number.
    """

    def post(self, request):
        serializer = self.get_serializer(data={
            "channel": "mobile",
            "identifier": request.data.get("mobile"),
            "otp": request.data.get("otp"),
            "password": request.data.get("password"),
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        add_alert(request, "Password reset successfully", level="success")
        return Response({"reset": True}, status=status.HTTP_200_OK)
