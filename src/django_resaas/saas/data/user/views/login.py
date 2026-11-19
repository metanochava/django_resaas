import re

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt import views as jwt_views
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.models.user_login import UserLogin
from django_resaas.saas.data.user.serializers.login import LoginSerializer
from django.contrib.auth import authenticate
from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin

class LoginAPIView(ResaasResponseMixin, generics.GenericAPIView):

    # PUBLIC (explicit): used before there is a session
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request):
        data = request.data.copy()  # now mutable
        identifier = data.get("identifier")
        password = data.get("password")
        data['id'] = identifier
        

        # defensive validations
        if not isinstance(identifier, str) or not isinstance(password, str):
            return Response(
                {"alert_error": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # minimal defensive validation

        serializer = self.serializer_class(
            data=data,
            context={'request': request}
        )


        serializer.is_valid(raise_exception=True)


        # data['user'] = serializer.data['id']

        


        # user_login = LoginSerializer(data=data)
        # user_login.is_valid(raise_exception=True)
        # user_login.save()
        
        response = serializer.data.copy()   # serializer data

        return Response(
            response,
            status=status.HTTP_200_OK,
        )


class RotatingTokenRefreshSerializer(TokenRefreshSerializer):
    """simplejwt's refresh, plus the session bookkeeping of the rotation
    (session_service.rotated) and the reuse of a rotated token
    (session_service.refresh_reused: the session family ends)."""

    def validate(self, attrs):
        from django_resaas.saas.core.services import session_service

        try:
            data = super().validate(attrs)
        except TokenError:
            session_service.refresh_reused(attrs.get("refresh"))
            raise
        if data.get("refresh"):
            session_service.rotated(data["refresh"])
        return data


class TokenRefreshView(ResaasResponseMixin, jwt_views.TokenRefreshView):
    """simplejwt's refresh, with the RESAAS response behaviour (error contract,
    POST status). PUBLIC (explicit, upstream): the caller only has a refresh token.
    With ROTATE_REFRESH_TOKENS the answer carries a new refresh token."""

    serializer_class = RotatingTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        """The refresh token of the body, else (a frontend of the API's own
        site) of its HttpOnly cookie (core/services/refresh_cookie.py)."""
        from rest_framework_simplejwt.exceptions import InvalidToken

        from django_resaas.saas.core.services import refresh_cookie

        refresh = request.data.get("refresh") or refresh_cookie.read(request)
        serializer = self.get_serializer(data={"refresh": refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
