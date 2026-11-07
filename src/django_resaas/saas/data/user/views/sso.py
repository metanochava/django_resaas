"""
Single sign-on between the frontend domains of one deployment
(core/services/sso_service.py):

    POST sso/code/   PROTECTED (a full session)
                     {redirect_uri, code_challenge} -> {code}
    POST sso/token/  PUBLIC (the caller has no session yet; the authorisation
                     is the single-use code + its PKCE verifier; throttled)
                     {code, code_verifier, redirect_uri, previous_refresh?}
                     -> tokens, like login/; the new session joins the family
                     of the one the code came from (and previous_refresh's,
                     the session this domain is replacing)
    POST sso/logout/ PROTECTED: ends this session and its whole family (every
                     domain of this browser) - {ended}
    GET  sso/redirect_check/?redirect_uri=
                     PUBLIC, read-only: whether redirect_uri is a trusted
                     destination (the central page uses it before sending a
                     visitor without a session back - never an open redirect)
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin
from django_resaas.saas.core.exceptions import error_response
from django_resaas.saas.core.services import session_service, sso_service
from django_resaas.saas.core.utils.translate import Translate
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
            user, source_jti = sso_service.redeem(
                request.data.get("code"),
                request.data.get("code_verifier"),
                request.data.get("redirect_uri"),
                request=request,
            )
        except sso_service.SsoError as error:
            return _error(request, error)

        family = session_service.sso_family_of(user, source_jti)
        previous = sso_service.previous_session(user, request.data.get("previous_refresh"))
        if previous:
            session_service.join_sso_family(user, family, previous)

        return self.session(request, user, sso_family=family)


class SsoLogoutAPIView(ResaasResponseMixin, generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        ended = sso_service.sign_out(request.user, request)

        return Response(
            {"ended": ended, "alert_success": Translate.tdc(request, "Logout successful")},
            status=status.HTTP_200_OK,
        )


class SsoRedirectCheckAPIView(_Public):
    throttle_classes = (SsoTokenThrottle,)

    def get(self, request):
        if not sso_service.allowed_redirect(request.query_params.get("redirect_uri") or ""):
            return _error(request, sso_service.SsoError("sso_invalid_redirect", "This site is not allowed to use the shared sign-in."))

        return Response({"allowed": True}, status=status.HTTP_200_OK)
