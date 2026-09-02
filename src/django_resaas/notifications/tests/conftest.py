import pytest

from django_resaas.notifications.enums import Category, Channel
from django_resaas.notifications.providers.fake import FakeProvider
from django_resaas.notifications.providers.registry import NotificationProviderRegistry


@pytest.fixture(autouse=True)
def notifications_enabled(settings):
    """The system kill switch (spec section 2) is off by default - every
    test in this app opts back in explicitly, exactly like a real
    deployment would."""

    settings.NOTIFICATIONS_ENABLED = True


@pytest.fixture(autouse=True)
def fake_providers():
    """Registers Fake* providers as the default for every channel before
    each test, and restores the real ones after - the test suite must
    never be able to reach a real Email/SMS/WhatsApp service (spec
    section 86)."""

    email = FakeProvider()
    sms = FakeProvider()
    whatsapp = FakeProvider()

    NotificationProviderRegistry.register(Channel.EMAIL, "django", email, default=True)
    NotificationProviderRegistry.register(Channel.SMS, "twilio", sms, default=True)
    NotificationProviderRegistry.register(
        Channel.WHATSAPP, "meta_cloud_api", whatsapp, default=True
    )

    yield {"email": email, "sms": sms, "whatsapp": whatsapp}

    NotificationProviderRegistry.unregister_all()
    from django_resaas.notifications.providers import register_default_providers

    register_default_providers()


@pytest.fixture
def notification_tenant(bootstrap_tenant, activate_module):
    """A tenant with the "sales" business module active (module-gate for
    NotificationRule.module) and notifications fully enabled for every
    channel (NotificationSettings) - the "everything configured and
    on" baseline most tests start from and then turn one thing off."""

    from django_resaas.notifications.models import NotificationSettings

    # "notifications" itself is an ordinary RESAAS module too (its
    # ViewSets extend BaseAPIView like any other resource) - activating
    # it is separate from "sales" being active, which only gates
    # sales.* *events*, not the notifications REST API surface.
    tenant = bootstrap_tenant("notif-user", modules=("sales", "notifications"))

    NotificationSettings.objects.create(
        entity=tenant["entity"],
        branch=None,
        email_enabled=True,
        sms_enabled=True,
        whatsapp_enabled=True,
    )

    return tenant


@pytest.fixture
def make_rule(notification_tenant):
    """Factory: create an enabled NotificationRule + a default-language
    NotificationTemplate for it in one call."""

    def _make(
        event="sales.sale.confirmed",
        channel=Channel.EMAIL,
        category=Category.TRANSACTIONAL,
        recipient_strategy="explicit",
        recipient_config=None,
        conditions=None,
        enabled=True,
        body="Hello {{ context_value }}",
        subject="Subject",
        **extra,
    ):
        from django_resaas.notifications.models import (
            NotificationRule,
            NotificationTemplate,
        )

        rule = NotificationRule.objects.create(
            entity=notification_tenant["entity"],
            branch=None,
            event=event,
            module="sales",
            channel=channel,
            category=category,
            enabled=enabled,
            recipient_strategy=recipient_strategy,
            recipient_config=recipient_config or {},
            conditions=conditions or {},
            **extra,
        )

        NotificationTemplate.objects.create(
            entity=notification_tenant["entity"],
            branch=None,
            rule=rule,
            language=None,
            subject=subject,
            body=body,
        )

        return rule

    return _make
