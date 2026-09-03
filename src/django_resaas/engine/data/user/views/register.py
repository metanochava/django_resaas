from rest_framework import generics, status
from rest_framework.response import Response

from django_resaas.engine.core.utils.translate import Translate
from django_resaas.engine.core.utils.username import UserName
from django_resaas.engine.data.user.serializers.register import RegisterSerializer


class RegisterAPIView(generics.GenericAPIView):
    """Completes registration for an identifier already OTP-verified via
    RequestRegisterOTPView. Does not auto-login - the account is created,
    the user logs in separately through the normal login flow."""

    serializer_class = RegisterSerializer

    def post(self, request):
        data = request.data.copy()

        if data.get("username"):
            data["username"] = UserName.Create(str(data["username"]).replace(" ", "_"))

        serializer = self.serializer_class(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "alert_success": Translate.tdc(
                    request, "Account created successfully"
                ),
                "data": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "mobile": user.mobile,
                },
            },
            status=status.HTTP_201_CREATED,
        )
