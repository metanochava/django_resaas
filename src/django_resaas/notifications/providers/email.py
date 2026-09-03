from django.conf import settings
from django.core.mail import EmailMultiAlternatives

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

    def send(
        self, recipient, subject=None, body=None, metadata=None, idempotency_key=None
    ):
        if not getattr(settings, "EMAIL_HOST", None) and not getattr(
            settings, "EMAIL_BACKEND", None
        ):
            raise ProviderConfigurationError(
                "EmailProvider: EMAIL_BACKEND/EMAIL_HOST is not configured."
            )

        try:
            message = EmailMultiAlternatives(
                subject=subject or "",
                body=body or "",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                to=[recipient],
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
