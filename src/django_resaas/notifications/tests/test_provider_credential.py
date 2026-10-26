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


# =====================================================================
# PLATFORM DEFAULT (entity=null)
# =====================================================================

PLATFORM_URL = "/api/notifications/platform-provider-credentials/"
TENANT_URL = "/api/notifications/provider-credentials/"


def _platform_sms(token="platform-token"):
    credential = NotificationProviderCredential(channel=Channel.SMS, provider_name="twilio")
    credential.set_config({"account_sid": "AC-platform", "auth_token": token, "from_number": "+1platform"})
    credential.save()
    return credential


def test_platform_row_is_used_without_entity(fake_providers):
    _platform_sms()

    provider = get_provider_for_entity(Channel.SMS)

    assert isinstance(provider, SMSProvider)
    assert provider._credentials()[1] == "platform-token"


def test_platform_row_is_used_by_a_tenant_without_override(notification_tenant, fake_providers):
    _platform_sms()

    provider = get_provider_for_entity(Channel.SMS, entity_id=notification_tenant["entity"].id)

    assert provider._credentials()[1] == "platform-token"


def test_tenant_override_beats_platform_row(notification_tenant, fake_providers):
    _platform_sms()
    tenant_row = NotificationProviderCredential(
        entity=notification_tenant["entity"], channel=Channel.SMS, provider_name="twilio",
    )
    tenant_row.set_config({"account_sid": "AC-t", "auth_token": "tenant-token", "from_number": "+1"})
    tenant_row.save()

    provider = get_provider_for_entity(Channel.SMS, entity_id=notification_tenant["entity"].id)

    assert provider._credentials()[1] == "tenant-token"


def test_inactive_platform_row_falls_back_to_env(fake_providers):
    credential = _platform_sms()
    credential.is_active = False
    credential.save()

    assert get_provider_for_entity(Channel.SMS) is fake_providers["sms"]


def test_one_platform_row_per_channel():
    from django.db import IntegrityError, transaction

    _platform_sms()

    with pytest.raises(IntegrityError), transaction.atomic():
        _platform_sms("second")


def test_branch_row_needs_an_entity(notification_tenant):
    from django.db import IntegrityError, transaction

    credential = NotificationProviderCredential(
        branch=notification_tenant["branch"], channel=Channel.SMS, provider_name="twilio",
    )
    credential.set_config({"auth_token": "x"})

    with pytest.raises(IntegrityError), transaction.atomic():
        credential.save()


def test_platform_level_creates_and_lists_platform_rows(notification_tenant):
    client = notification_tenant["client"]  # Root: platform level

    response = client.post(PLATFORM_URL, {
        "channel": "sms", "provider_name": "twilio",
        "config": {"account_sid": "AC-new", "auth_token": "new-secret", "from_number": "+1"},
    }, format="json")

    assert response.status_code == 201, response.json()
    assert "config" not in response.json()
    assert "new-secret" not in response.content.decode()

    row = NotificationProviderCredential.objects.get(id=response.json()["id"])
    assert row.entity_id is None and row.branch_id is None
    assert row.get_config()["auth_token"] == "new-secret"

    listed = client.get(PLATFORM_URL).json()
    items = listed["results"] if isinstance(listed, dict) else listed
    assert [item["id"] for item in items] == [str(row.id)]
    assert "new-secret" not in client.get(PLATFORM_URL).content.decode()


def test_platform_view_never_shows_entity_rows(notification_tenant):
    tenant_row = NotificationProviderCredential(
        entity=notification_tenant["entity"], channel=Channel.EMAIL, provider_name="django",
    )
    tenant_row.set_config({"host": "smtp.tenant.example.com"})
    tenant_row.save()

    client = notification_tenant["client"]
    listed = client.get(PLATFORM_URL).json()
    items = listed["results"] if isinstance(listed, dict) else listed

    assert items == []
    assert client.get(f"{PLATFORM_URL}{tenant_row.id}/").status_code == 404


def test_tenant_view_never_shows_platform_rows(notification_tenant):
    platform_row = _platform_sms()
    client = notification_tenant["client"]

    listed = client.get(TENANT_URL).json()
    items = listed["results"] if isinstance(listed, dict) else listed

    assert str(platform_row.id) not in [item["id"] for item in items]
    assert client.get(f"{TENANT_URL}{platform_row.id}/").status_code == 404
    assert client.delete(f"{TENANT_URL}{platform_row.id}/").status_code == 404


def test_below_platform_level_is_forbidden(notification_tenant):
    from django.contrib.auth.models import Permission
    from rest_framework.test import APIClient

    from django_resaas.saas.core.tenant.context import ResaasContextService
    from django_resaas.saas.models.branch_user import BranchUser
    from django_resaas.saas.models.branch_user_group import BranchUserGroup
    from django_resaas.saas.models.entity_group import EntityGroup
    from django_resaas.saas.models.entity_user import EntityUser
    from django_resaas.saas.models.group import Group
    from django_resaas.saas.models.user import User

    platform_row = _platform_sms()
    tenant = notification_tenant
    user = User.objects.create_user(username="cred-admin", email="cred-admin@example.com", password="pass-12345")
    EntityUser.objects.get_or_create(user=user, entity=tenant["entity"])
    BranchUser.objects.get_or_create(user=user, branch=tenant["branch"])
    group = Group.objects.create(name="Credentials Admin")
    EntityGroup.objects.create(entity=tenant["entity"], group=group, state="Active")
    # every model permission of the credentials, but not platform level
    group.permissions.set(Permission.objects.filter(codename__endswith="_notificationprovidercredential"))
    BranchUserGroup.objects.create(user=user, group=group, branch=tenant["branch"])
    context = ResaasContextService.issue(
        user=user, entity_id=tenant["entity"].id, branch_id=tenant["branch"].id, group_id=group.id,
    )
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")

    assert client.get(PLATFORM_URL).status_code == 403
    assert client.post(PLATFORM_URL, {
        "channel": "email", "provider_name": "django", "config": {"host": "smtp.evil.example.com"},
    }, format="json").status_code == 403
    assert client.patch(f"{PLATFORM_URL}{platform_row.id}/", {"is_active": False}, format="json").status_code == 403
    assert client.delete(f"{PLATFORM_URL}{platform_row.id}/").status_code == 403

    platform_row.refresh_from_db()
    assert platform_row.is_active is True
    assert not NotificationProviderCredential.objects.filter(channel=Channel.EMAIL).exists()


def test_anonymous_cannot_reach_platform_rows():
    from rest_framework.test import APIClient

    assert APIClient().get(PLATFORM_URL).status_code in (401, 403)


def test_password_reset_email_uses_the_platform_row(fake_providers, monkeypatch, rf, settings):
    """Pre-session sends (password reset, OTP, welcome) resolve through
    the same chain: platform row first, then the env/settings default."""
    from django_resaas.saas.core.services import password_reset_service
    from django_resaas.saas.models.user import User

    settings.CORS_ALLOWED_ORIGINS = ["https://app.platform.test"]
    credential = NotificationProviderCredential(channel=Channel.EMAIL, provider_name="django")
    credential.set_config({"host": "smtp.platform.example.com", "from_email": "noreply@platform.example.com"})
    credential.save()
    used = {}

    def _send(self, recipient, subject=None, body=None, metadata=None, idempotency_key=None):
        used.update(host=self._override.get("host"), recipient=recipient)
        return {"success": True}

    monkeypatch.setattr(EmailProvider, "send", _send)
    user = User.objects.create_user(username="reset-platform", email="reset@platform.test", password="pass-12345")
    request = rf.post("/", HTTP_ORIGIN="https://app.platform.test")
    request.lang_id = None

    password_reset_service.send_link(request, user, "email")

    assert used == {"host": "smtp.platform.example.com", "recipient": "reset@platform.test"}
