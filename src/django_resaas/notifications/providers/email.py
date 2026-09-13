from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from django_resaas.notifications.exceptions import (
    ProviderConfigurationError,
    ProviderTemporaryError,
)
from .base import BaseNotificationProvider


class EmailProvider(BaseNotificationProvider):
    """Uses django.core.mail as-is - whatever EMAIL_BACKEND/EMAIL_HOST*
    the project already has configured (spec section 16: don't reinvent
    SMTP). Swapping to SES/SendGrid/Mailgun later only means changing
    EMAIL_BACKEND - this provider never changes."""

    name = "django"

    def __init__(self, credentials=None):
        """`credentials`, when given, overrides the project's global
        EMAIL_* settings with an explicit SMTP connection for this send
        only - see SMSProvider.__init__ for the general pattern.
        Expected keys: host, port, username, password, use_tls,
        use_ssl, from_email."""
        self._override = credentials or {}

    def send(
        self, recipient, subject=None, body=None, metadata=None, idempotency_key=None
    ):
        connection = None
        from_email = self._override.get("from_email") or getattr(settings, "DEFAULT_FROM_EMAIL", None)

        if self._override:
            if not self._override.get("host"):
                raise ProviderConfigurationError(
                    "EmailProvider: tenant override is missing 'host'."
                )
            connection = get_connection(
                backend="django.core.mail.backends.smtp.EmailBackend",
                host=self._override.get("host"),
                port=self._override.get("port"),
                username=self._override.get("username"),
                password=self._override.get("password"),
                use_tls=self._override.get("use_tls", False),
                use_ssl=self._override.get("use_ssl", False),
                fail_silently=False,
            )
        elif not getattr(settings, "EMAIL_HOST", None) and not getattr(
            settings, "EMAIL_BACKEND", None
        ):
            raise ProviderConfigurationError(
                "EmailProvider: EMAIL_BACKEND/EMAIL_HOST is not configured."
            )

        try:
            message = EmailMultiAlternatives(
                subject=subject or "",
                body=body or "",
                from_email=from_email,
                to=[recipient],
                connection=connection,
            )

            html = (metadata or {}).get("html")
            if html:
                message.attach_alternative(html, "text/html")

            sent = message.send(fail_silently=False)
        except Exception as exc:
            # SMTP connection issues are transient by nature.
            raise ProviderTemporaryError(str(exc)) from exc

        return {
            "success": bool(sent),
            "provider_message_id": None,  # SMTP has no message id
            "provider_status": "sent" if sent else "not_sent",
            "raw": {"sent_count": sent},
        }
