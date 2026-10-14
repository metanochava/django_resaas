"""Password reset ("forgot my password"), before there is a session.

Two channels - the account's e-mail or its phone number (User.email /
User.mobile, both unique) - and two methods, chosen by the person:

    link  a one-time link (Django's PasswordResetTokenGenerator: invalid once
          the password changes) to the frontend page /#/auth/resetpassword/
          <uidb64>/<token>, completed by PATCH password/reset/complete/
    otp   a 6-digit code (otp_service, TOTP bound to the identifier AND to the
          purpose "password_reset", 5 minutes), completed by
          POST password/reset/otp/complete/

The link is built only on a trusted frontend origin: the request's Origin when
the CORS policy allows it (CORS_ALLOWED_ORIGINS / CORS_ALLOWED_ORIGIN_REGEXES),
else settings/env FRONTEND_URL. An Origin outside the policy is never used, so
a reset cannot be "poisoned" into mailing a link to someone else's domain.

Delivery is synchronous through the notification providers (the person waits
on screen), like otp_service.
"""
import os
import re

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_bytes
from django.utils.http import urlsafe_base64_encode

from django_resaas.notifications.enums import Channel
from django_resaas.notifications.exceptions import NotificationError
from django_resaas.notifications.providers import NotificationProviderRegistry
from django_resaas.saas.core.services.otp_service import send_registration_otp
from django_resaas.saas.core.utils.templates import render_email_template
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.models.user import User

PURPOSE = "password_reset"
CHANNELS = ("email", "mobile")
METHODS = ("link", "otp")


class ResetLinkUnavailable(Exception):
    """No trusted frontend origin to build the link on."""


def normalize(channel, identifier):
    value = str(identifier or "").strip()
    return value.lower() if channel == "email" else value.replace(" ", "")


def find_user(channel, identifier):
    """The active account of an e-mail / phone number, or None."""
    if not identifier:
        return None
    users = User.objects.filter(is_active=True)
    if channel == "email":
        return users.filter(email__iexact=identifier).first()
    return users.filter(mobile=identifier).first()


def _trusted_origin(request):
    origin = (request.META.get("HTTP_ORIGIN", "") if request else "").rstrip("/")
    if origin:
        allowed = [item.rstrip("/") for item in getattr(settings, "CORS_ALLOWED_ORIGINS", []) if item]
        patterns = getattr(settings, "CORS_ALLOWED_ORIGIN_REGEXES", [])
        if getattr(settings, "CORS_ORIGIN_ALLOW_ALL", False) is not True and (
            origin in allowed or any(re.match(pattern, origin) for pattern in patterns)
        ):
            return origin
    fallback = getattr(settings, "FRONTEND_URL", None) or os.environ.get("FRONTEND_URL", "")
    return fallback.rstrip("/") or None


def link_available(request):
    """Whether a link can be built for this request. Asked BEFORE looking the
    account up, so the answer never depends on whether the account exists."""
    return _trusted_origin(request) is not None


def reset_link(request, user):
    base = _trusted_origin(request)
    if not base:
        raise ResetLinkUnavailable()
    uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
    token = PasswordResetTokenGenerator().make_token(user)
    # the frontend route (hash routing): quasar_resaas authRoutes 'resetPasswordConfirm'
    return f"{base}/#/auth/resetpassword/{uidb64}/{token}"


def send_link(request, user, channel):
    """Sends the reset link to the user's e-mail or phone. Raises
    ResetLinkUnavailable or a NotificationError subclass."""
    link = reset_link(request, user)

    if channel == "email":
        html = render_email_template("PASSWORD_RESET", {
            "link": link,
            "greeting": Translate.tdc(request, "Hi {username},").format(username=user.username),
            "intro": Translate.tdc(
                request,
                "We received a request to reset your password. Click the button below to choose a new one.",
            ),
            "button_label": Translate.tdc(request, "Reset password"),
            "ignore_notice": Translate.tdc(request, "If you didn't request this, you can safely ignore this email."),
            "footer_notice": Translate.tdc(request, "This is an automated message, please do not reply."),
        }, request=request)
        provider = NotificationProviderRegistry.get(Channel.EMAIL)
        if provider is None:
            raise NotificationError("No provider registered for channel='email'.")
        provider.send(
            recipient=user.email,
            subject=Translate.tdc(request, "Password reset"),
            body=link,
            metadata={"html": html},
        )
        return

    provider = NotificationProviderRegistry.get(Channel.SMS)
    if provider is None:
        raise NotificationError("No provider registered for channel='sms'.")
    provider.send(
        recipient=user.mobile,
        body=Translate.tdc(request, "Use this link to reset your password: {link}").format(link=link),
    )


def send_code(request, channel, identifier):
    """Sends a reset code to the (normalized) e-mail or phone - the same
    identifier the code is later verified with. NotificationError on failure."""
    send_registration_otp(channel, identifier, request=request, purpose=PURPOSE)
