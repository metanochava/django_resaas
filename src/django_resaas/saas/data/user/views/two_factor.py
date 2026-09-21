"""
Two-factor authentication endpoints.

SELF-SERVICE (authenticated, always about request.user; the account owner is the
authorisation, like password/change/*):
    GET  two_factor/                      state, effective policy, codes left
    POST two_factor/setup/                start enrolment  -> secret, QR, otpauth
    POST two_factor/confirm/     {code}   prove the first code -> recovery codes
    POST two_factor/disable/     {code}   turn it off (refused when REQUIRED)
    POST two_factor/recovery/    {code}   new recovery codes (old ones die)

SIGN-IN (deliberately PUBLIC - explicit AllowAny, no authentication classes: the
caller has no session yet). The authorisation is the signed, 5-minute challenge
issued by the password step, plus the TOTP / recovery code itself:
    POST login/two_factor/                {challenge, code}  -> tokens
    POST login/two_factor/setup/          {challenge}        -> secret, QR
    POST login/two_factor/setup/confirm/  {challenge, code}  -> tokens + recovery codes
"""
from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django_resaas.saas.core.exceptions import error_response
from django_resaas.saas.core.services import session_service, two_factor_service as service
from django_resaas.saas.core.utils.translate import Translate


def _entity(request):
    from django_resaas.saas.models.entity import Entity

    entity_id = getattr(request, "entity_id", None)

    return Entity.objects.filter(pk=entity_id).first() if entity_id else None


def _error(request, error):
    return error_response(request, error.message, error.http_status, code=error.code)


def _setup_payload(user):
    started = service.begin_setup(user)

    return {
        "secret": started["secret"],
        "otpauth_uri": started["otpauth_uri"],
        "qr": service.qr_data_uri(started["otpauth_uri"]),
    }


def _code(request):
    value = request.data.get("code")

    return value if isinstance(value, str) else ""


class _Base(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)


class TwoFactorStatusAPIView(_Base):
    def get(self, request):
        return Response(service.details(request.user, _entity(request)), status=status.HTTP_200_OK)


class TwoFactorSetupAPIView(_Base):
    def post(self, request):
        if not service.details(request.user, _entity(request))["can_setup"]:
            return error_response(request, "Two-factor authentication is not available for your organisation.", status.HTTP_403_FORBIDDEN, code="two_factor_disabled")

        try:
            return Response(_setup_payload(request.user), status=status.HTTP_200_OK)
        except service.TwoFactorError as error:
            return _error(request, error)


class TwoFactorConfirmAPIView(_Base):
    def post(self, request):
        try:
            codes = service.confirm_setup(request.user, _code(request), request=request)
        except service.TwoFactorError as error:
            return _error(request, error)

        return Response(
            {"recovery_codes": codes, "alert_success": Translate.tdc(request, "Two-factor authentication enabled")},
            status=status.HTTP_200_OK,
        )


class TwoFactorDisableAPIView(_Base):
    def post(self, request):
        try:
            service.disable(request.user, _code(request), request=request)
        except service.TwoFactorError as error:
            return _error(request, error)

        return Response({"alert_success": Translate.tdc(request, "Two-factor authentication disabled")}, status=status.HTTP_200_OK)


class TwoFactorRecoveryAPIView(_Base):
    def post(self, request):
        try:
            codes = service.regenerate_recovery_codes(request.user, _code(request), request=request)
        except service.TwoFactorError as error:
            return _error(request, error)

        return Response(
            {"recovery_codes": codes, "alert_success": Translate.tdc(request, "New recovery codes generated")},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------- sign-in

class _Public(generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def challenge_user(self, request, purpose):
        challenge = request.data.get("challenge")

        return service.read_challenge(challenge if isinstance(challenge, str) else "", purpose)

    def session(self, request, user, extra=None):
        tokens = user.tokens()
        session_service.record_login(user, request, tokens)

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "mobile": user.mobile,
                "must_change_password": False,
                "two_factor": "",
                "challenge": "",
                "tokens": tokens,
                **(extra or {}),
            },
            status=status.HTTP_200_OK,
        )


class LoginTwoFactorAPIView(_Public):
    def post(self, request):
        try:
            user = self.challenge_user(request, service.LOGIN)
            service.verify(user, _code(request), request=request)
        except service.TwoFactorError as error:
            return _error(request, error)

        return self.session(request, user)


class LoginTwoFactorSetupAPIView(_Public):
    """Enrolment forced by a REQUIRED policy, before the first session."""

    def post(self, request):
        try:
            user = self.challenge_user(request, service.SETUP)

            if not service.requires_two_factor(user):
                raise service.TwoFactorError("invalid_challenge", "This sign-in step has expired. Sign in again.", 401)

            return Response(_setup_payload(user), status=status.HTTP_200_OK)
        except service.TwoFactorError as error:
            return _error(request, error)


class LoginTwoFactorSetupConfirmAPIView(_Public):
    def post(self, request):
        try:
            user = self.challenge_user(request, service.SETUP)
            codes = service.confirm_setup(user, _code(request), request=request)
        except service.TwoFactorError as error:
            return _error(request, error)

        return self.session(request, user, {"recovery_codes": codes})
