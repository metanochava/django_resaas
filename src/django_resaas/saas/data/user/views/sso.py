"""
Single sign-on between the frontend domains of one deployment
(core/services/sso_service.py):

    POST sso/code/   PROTECTED (a full session)
                     {redirect_uri, code_challenge} -> {code}
    POST sso/token/  PUBLIC (the caller has no session yet; the authorisation
                     is the single-use code + its PKCE verifier; throttled)
                     {code, code_verifier, redirect_uri} -> tokens, like login/
    GET  sso/redirect_check/?redirect_uri=
                     PUBLIC, read-only: whether redirect_uri is a trusted
                     destination (the central page uses it before sending a
                     visitor without a session back - never an open redirect)
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin
from django_resaas.saas.core.exceptions import error_response
from django_resaas.saas.core.services import sso_service
from django_resaas.saas.data.user.views.registration_throttles import SsoTokenThrottle
from django_resaas.saas.data.user.views.two_factor import _Public


def _error(request, error):
    return error_response(request, error.message, error.http_status, code=error.code)


class SsoCodeAPIView(ResaasResponseMixin, generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            code = sso_service.issue_code(
                request.user,
                request.data.get("redirect_uri"),
                request.data.get("code_challenge"),
                request=request,
            )
        except sso_service.SsoError as error:
            return _error(request, error)

        return Response({"code": code, "expires_in": sso_service.CODE_TTL}, status=status.HTTP_200_OK)


class SsoTokenAPIView(_Public):
    throttle_classes = (SsoTokenThrottle,)

    def post(self, request):
        try:
            user = sso_service.redeem(
                request.data.get("code"),
                request.data.get("code_verifier"),
                request.data.get("redirect_uri"),
                request=request,
            )
        except sso_service.SsoError as error:
            return _error(request, error)

        return self.session(request, user)


class SsoRedirectCheckAPIView(_Public):
    throttle_classes = (SsoTokenThrottle,)

    def get(self, request):
        if not sso_service.allowed_redirect(request.query_params.get("redirect_uri") or ""):
            return _error(request, sso_service.SsoError("sso_invalid_redirect", "This site is not allowed to use the shared sign-in."))

        return Response({"allowed": True}, status=status.HTTP_200_OK)
