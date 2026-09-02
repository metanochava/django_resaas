from .base import BaseNotificationProvider
from .registry import NotificationProviderRegistry

__all__ = ["BaseNotificationProvider", "NotificationProviderRegistry"]


def register_default_providers():
    """Registers the real Email/SMS/WhatsApp providers as each channel's
    default. Called once from NotificationsConfig.ready(). Tests should
    call NotificationProviderRegistry.register(channel, name, FakeX(),
    default=True) to override - never leave a real provider registered
    as default while running the test suite."""

    from .email import EmailProvider
    from .sms import SMSProvider
    from .whatsapp import WhatsAppProvider

    NotificationProviderRegistry.register(
        "email", "django", EmailProvider(), default=True
    )
    NotificationProviderRegistry.register("sms", "twilio", SMSProvider(), default=True)
    NotificationProviderRegistry.register(
        "whatsapp", "meta_cloud_api", WhatsAppProvider(), default=True
    )
