from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django_resaas.saas.core.services import session_service, temporary_password_service
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.data.user.serializers.login import authenticate

MIN_LENGTH = 8


class ChangeTemporaryPasswordAPIView(generics.GenericAPIView):
    """
    POST password/change/temporary/  {identifier, password, new_password}

    The first-login step: the user proves the TEMPORARY password and chooses a
    definitive one; only then does a session (tokens) exist. Deliberately
    PUBLIC (explicit AllowAny, no authentication classes): the caller has no
    session yet - the temporary credential itself is the authorisation, and it
    is only accepted while it is still a valid temporary password. Nothing is
    revealed on failure (same answer for unknown user / wrong password /
    permanent password).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def _fail(self, request, code, message, http_status=status.HTTP_400_BAD_REQUEST):
        return Response({"code": code, "detail": Translate.tdc(request, message)}, status=http_status)

    def post(self, request):
        identifier = request.data.get("identifier")
        password = request.data.get("password")
        new_password = request.data.get("new_password")

        if not all(isinstance(value, str) and value for value in (identifier, password, new_password)):
            return self._fail(request, "invalid_request", "Invalid credentials")

        user = authenticate(value=identifier.strip(), password=password)

        if user is None or not user.is_active:
            return self._fail(request, "invalid_credentials", "Invalid credentials", status.HTTP_401_UNAUTHORIZED)

        state = temporary_password_service.state_of(user)

        if state == temporary_password_service.EXPIRED:
            return self._fail(request, "temporary_password_expired", "The temporary password has expired. Ask an administrator for a new one.", status.HTTP_401_UNAUTHORIZED)

        if state != temporary_password_service.TEMPORARY:
            # a definitive password is changed through the normal flows
            return self._fail(request, "invalid_credentials", "Invalid credentials", status.HTTP_401_UNAUTHORIZED)

        if len(new_password) < MIN_LENGTH:
            return self._fail(request, "password_too_short", "The password must be at least 8 characters long")

        if new_password == password:
            return self._fail(request, "password_unchanged", "The new password must be different from the temporary one")

        temporary_password_service.complete(user, new_password)

        tokens = user.tokens()
        session_service.record_login(user, request, tokens)

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "mobile": user.mobile,
                "must_change_password": False,
                "tokens": tokens,
                "alert_success": Translate.tdc(request, "Password changed successfully"),
            },
            status=status.HTTP_200_OK,
        )
