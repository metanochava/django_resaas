"""
The signed-in user's OWN security overview: active sessions (and ending them)
and recent security activity. Self-service endpoints - authenticated, always
about request.user, never about another user (an administrator's view of
someone else's password is the separate, permission-gated UserAPIView action).
They are not model actions, so they carry no permission codename: like
password/change/*, the account owner is the authorisation.
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from django_resaas.saas.core.services import session_service
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.models.audit_log import AuditLog
from django_resaas.saas.models.user_login import UserLogin

# the account's own security events worth showing to its owner (an
# administrator revealing a temporary password is deliberately NOT one of them)
OWN_EVENTS = ("PASSWORD_CHANGED", "TEMPORARY_PASSWORD_CHANGED", "EMAIL_CHANGED", "MOBILE_CHANGED", "TWO_FACTOR_ENABLED", "TWO_FACTOR_DISABLED", "TWO_FACTOR_RECOVERY_USED", "TWO_FACTOR_RECOVERY_REGENERATED")
LIMIT = 30


class SessionsAPIView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        current = session_service.current_session_id(request)

        return Response(
            {"data": session_service.active_sessions(request.user, current)},
            status=status.HTTP_200_OK,
        )


class TerminateSessionAPIView(generics.GenericAPIView):
    """POST sessions/<jti>/terminate/ - end one of YOUR sessions."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, jti):
        if jti == session_service.current_session_id(request):
            return Response(
                {"code": "cannot_terminate_current_session", "detail": Translate.tdc(request, "Use sign out to end the current session.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not session_service.terminate(request.user, jti):
            return Response(
                {"code": "session_not_found", "detail": Translate.tdc(request, "Session not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"alert_success": Translate.tdc(request, "Session ended.")}, status=status.HTTP_200_OK)


class TerminateOtherSessionsAPIView(generics.GenericAPIView):
    """POST sessions/terminate_others/ - end every session but this one."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        current = session_service.current_session_id(request)

        if not current:
            # a token issued before sessions existed cannot say which one it is
            return Response(
                {"code": "current_session_unknown", "detail": Translate.tdc(request, "Sign in again to manage your other sessions.")},
                status=status.HTTP_409_CONFLICT,
            )

        count = session_service.terminate_others(request.user, current)

        return Response({"count": count, "alert_success": Translate.tdc(request, "Other sessions ended.")}, status=status.HTTP_200_OK)


class SecurityActivityAPIView(generics.GenericAPIView):
    """GET security/activity/ - recent sign-ins and changes to YOUR account."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        events = [
            {"type": "login", "at": login.created_at, "device": login.dispositivo or ""}
            for login in UserLogin.objects.filter(user=request.user).order_by("-created_at")[:LIMIT]
        ]

        events += [
            {"type": event.action, "at": event.created_at, "device": ""}
            for event in AuditLog.objects.filter(
                model="User", object_id=str(request.user.pk), action__in=OWN_EVENTS
            ).order_by("-created_at")[:LIMIT]
        ]

        events.sort(key=lambda event: event["at"], reverse=True)

        return Response({"data": events[:LIMIT]}, status=status.HTTP_200_OK)
