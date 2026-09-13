"""
Per-tenant provider credential override: a tenant's own
NotificationProviderCredential must take priority over the platform-
wide (env var) default, must never leak in plaintext anywhere, and
must fall back cleanly when there is no active override.
"""
import pytest

from django_resaas.notifications.crypto import decrypt_config, encrypt_config
from django_resaas.notifications.enums import Channel
from django_resaas.notifications.models import NotificationProviderCredential
from django_resaas.notifications.providers.email import EmailProvider
from django_resaas.notifications.providers.sms import SMSProvider
from django_resaas.notifications.providers.whatsapp import WhatsAppProvider
from django_resaas.notifications.tenant_credentials import get_provider_for_entity

pytestmark = pytest.mark.django_db


# =====================================================================
# CRYPTO
# =====================================================================


def test_encrypt_decrypt_round_trips():
    config = {"account_sid": "AC123", "auth_token": "secret", "from_number": "+15550000"}

    ciphertext = encrypt_config(config)

    assert ciphertext != str(config)
    assert "secret" not in ciphertext
    assert decrypt_config(ciphertext) == config


# =====================================================================
# MODEL
# =====================================================================


def test_model_never_stores_plaintext(notification_tenant):
    credential = NotificationProviderCredential(
        entity=notification_tenant["entity"],
        channel=Channel.SMS,
        provider_name="twilio",
    )
    credential.set_config({"account_sid": "AC123", "auth_token": "top-secret", "from_number": "+1"})
    credential.save()

    credential.refresh_from_db()

    assert "top-secret" not in credential.encrypted_config
    assert credential.get_config()["auth_token"] == "top-secret"


# =====================================================================
# RESOLVER
# =====================================================================


def test_falls_back_to_platform_default_when_no_override(notification_tenant, fake_providers):
    provider = get_provider_for_entity(Channel.SMS, entity_id=notification_tenant["entity"].id)

    assert provider is fake_providers["sms"]


def test_falls_back_to_platform_default_without_entity(fake_providers):
    provider = get_provider_for_entity(Channel.SMS)

    assert provider is fake_providers["sms"]


def test_entity_wide_override_takes_priority(notification_tenant, fake_providers):
    credential = NotificationProviderCredential(
        entity=notification_tenant["entity"],
        channel=Channel.SMS,
        provider_name="twilio",
    )
    credential.set_config({"account_sid": "AC-tenant", "auth_token": "tenant-token", "from_number": "+15551234"})
    credential.save()

    provider = get_provider_for_entity(Channel.SMS, entity_id=notification_tenant["entity"].id)

    assert isinstance(provider, SMSProvider)
    assert provider is not fake_providers["sms"]
    assert provider._credentials() == ("AC-tenant", "tenant-token", "+15551234")


def test_inactive_override_is_ignored(notification_tenant, fake_providers):
    credential = NotificationProviderCredential(
        entity=notification_tenant["entity"],
        channel=Channel.SMS,
        provider_name="twilio",
        is_active=False,
    )
    credential.set_config({"account_sid": "AC-x", "auth_token": "x", "from_number": "+1"})
    credential.save()

    provider = get_provider_for_entity(Channel.SMS, entity_id=notification_tenant["entity"].id)

    assert provider is fake_providers["sms"]


def test_branch_override_takes_priority_over_entity_wide(notification_tenant, fake_providers):
    entity = notification_tenant["entity"]
    branch = notification_tenant["branch"]

    entity_wide = NotificationProviderCredential(entity=entity, channel=Channel.WHATSAPP, provider_name="meta_cloud_api")
    entity_wide.set_config({"token": "entity-token", "phone_number_id": "111"})
    entity_wide.save()

    branch_specific = NotificationProviderCredential(entity=entity, branch=branch, channel=Channel.WHATSAPP, provider_name="meta_cloud_api")
    branch_specific.set_config({"token": "branch-token", "phone_number_id": "222"})
    branch_specific.save()

    provider_for_branch = get_provider_for_entity(Channel.WHATSAPP, entity_id=entity.id, branch_id=branch.id)
    provider_for_other_branch = get_provider_for_entity(Channel.WHATSAPP, entity_id=entity.id, branch_id=999999)

    assert isinstance(provider_for_branch, WhatsAppProvider)
    assert provider_for_branch._credentials()[0] == "branch-token"

    # a different/no branch falls back to the entity-wide row, not the
    # other branch's override
    assert provider_for_other_branch._credentials()[0] == "entity-token"


def test_provider_name_mismatch_is_not_used(notification_tenant, fake_providers):
    """A rule pinned to a specific provider name must not pick up a
    tenant override configured for a different provider - falling
    through to NotificationProviderRegistry.get(channel, name), whose
    existing contract is to return None for an unregistered name
    (unchanged by this feature)."""
    credential = NotificationProviderCredential(
        entity=notification_tenant["entity"], channel=Channel.SMS, provider_name="twilio",
    )
    credential.set_config({"account_sid": "AC-x", "auth_token": "x", "from_number": "+1"})
    credential.save()

    provider = get_provider_for_entity(
        Channel.SMS, entity_id=notification_tenant["entity"].id, provider_name="some_other_provider",
    )

    assert provider is None


# =====================================================================
# PROVIDER OVERRIDE (constructor-level, no DB)
# =====================================================================


def test_sms_provider_override_takes_priority_over_env(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "env-sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "env-token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+1env")

    provider = SMSProvider(credentials={"account_sid": "override-sid"})

    account_sid, auth_token, from_number = provider._credentials()

    assert account_sid == "override-sid"
    assert auth_token == "env-token"  # falls back to env for keys not overridden
    assert from_number == "+1env"


def test_whatsapp_provider_with_no_override_uses_env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_CLOUD_API_TOKEN", "env-token")
    monkeypatch.setenv("WHATSAPP_CLOUD_API_PHONE_NUMBER_ID", "env-phone-id")

    provider = WhatsAppProvider()

    token, phone_number_id, _ = provider._credentials()

    assert token == "env-token"
    assert phone_number_id == "env-phone-id"


# =====================================================================
# EMAIL
# =====================================================================


def test_email_provider_without_override_uses_no_explicit_connection(monkeypatch, settings):
    settings.EMAIL_HOST = "smtp.default.example.com"
    captured = {}

    class _FakeMessage:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def attach_alternative(self, *a, **k):
            pass

        def send(self, fail_silently=False):
            return 1

    monkeypatch.setattr(
        "django_resaas.notifications.providers.email.EmailMultiAlternatives", _FakeMessage,
    )

    result = EmailProvider().send(recipient="a@example.com", subject="Hi", body="Hello")

    assert result["success"] is True
    assert captured["connection"] is None


def test_email_provider_with_override_builds_explicit_smtp_connection(monkeypatch):
    captured = {}

    class _FakeMessage:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def attach_alternative(self, *a, **k):
            pass

        def send(self, fail_silently=False):
            return 1

    monkeypatch.setattr(
        "django_resaas.notifications.providers.email.EmailMultiAlternatives", _FakeMessage,
    )

    provider = EmailProvider(credentials={
        "host": "smtp.tenant.example.com", "port": 587, "username": "u", "password": "p",
        "use_tls": True, "from_email": "tenant@example.com",
    })
    result = provider.send(recipient="a@example.com", subject="Hi", body="Hello")

    assert result["success"] is True
    assert captured["connection"] is not None
    assert captured["connection"].host == "smtp.tenant.example.com"
    assert captured["from_email"] == "tenant@example.com"


def test_email_provider_override_missing_host_raises_configuration_error():
    from django_resaas.notifications.exceptions import ProviderConfigurationError

    provider = EmailProvider(credentials={"username": "u"})

    with pytest.raises(ProviderConfigurationError):
        provider.send(recipient="a@example.com", body="Hello")


def test_email_tenant_override_is_used_by_resolver(notification_tenant, fake_providers):
    credential = NotificationProviderCredential(
        entity=notification_tenant["entity"], channel=Channel.EMAIL, provider_name="django",
    )
    credential.set_config({"host": "smtp.tenant.example.com", "from_email": "tenant@example.com"})
    credential.save()

    provider = get_provider_for_entity(Channel.EMAIL, entity_id=notification_tenant["entity"].id)

    assert isinstance(provider, EmailProvider)
    assert provider is not fake_providers["email"]
    assert provider._override["host"] == "smtp.tenant.example.com"
