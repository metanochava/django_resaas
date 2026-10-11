from rest_framework import generics, status, permissions
from rest_framework.response import Response

from django_resaas.saas.core.alerts import add_alert
from django_resaas.saas.core.exceptions import error_response
from django_resaas.saas.core.services.registration_welcome_service import send_registration_welcome
from django_resaas.saas.core.utils.username import normalize_username, username_is_taken, username_is_valid
from django_resaas.saas.data.user.serializers.register import RegisterSerializer
from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin
from django_resaas.saas.data.user.views.registration_throttles import RegisterThrottle, UsernameCheckThrottle

# names checked in one request (the form checks its suggestions together)
MAX_USERNAME_CANDIDATES = 8


class RegisterAPIView(ResaasResponseMixin, generics.GenericAPIView):
    """Completes registration for an identifier already OTP-verified via
    RequestRegisterOTPView. Does not auto-login - the account is created,
    the user logs in separately through the normal login flow. Creates no
    Entity / Branch / profile membership."""

    # PUBLIC (explicit): used before there is a session
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (RegisterThrottle,)

    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        send_registration_welcome(
            user, channel=serializer.validated_data.get("channel"), request=request,
        )

        add_alert(request, "Account created successfully", level="success")
        return Response(
            {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "mobile": user.mobile,
            },
            status=status.HTTP_201_CREATED,
        )


class UsernameAvailabilityAPIView(ResaasResponseMixin, generics.GenericAPIView):
    """GET register/username/?candidates=a,b,c - whether each name can be used
    as a username right now: {"username", "valid", "available"} per name, in the
    order asked. Says nothing about the account holding a taken name. Only
    indicative: registration checks again and the UNIQUE constraint decides."""

    # PUBLIC (explicit): the registration form asks before there is a session
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (UsernameCheckThrottle,)

    def get(self, request):
        raw = request.query_params.get("candidates") or request.query_params.get("username") or ""
        names = []
        for value in raw.split(","):
            name = normalize_username(value)
            if name and name not in names:
                names.append(name)

        if not names:
            return error_response(request, "Give a username to check", status.HTTP_400_BAD_REQUEST, code="username_required")

        results = []
        for name in names[:MAX_USERNAME_CANDIDATES]:
            valid = username_is_valid(name)
            results.append({
                "username": name,
                "valid": valid,
                "available": valid and not username_is_taken(name),
            })

        return Response({"results": results}, status=status.HTTP_200_OK)
