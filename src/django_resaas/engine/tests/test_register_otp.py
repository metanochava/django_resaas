"""
Registration-by-OTP (email or mobile) and the three pre-existing
password-reset bugs fixed alongside it:

1. RequestPasswordResetEmailAPIView used to crash with NoReverseMatch
   (reverse('password-reset-confirm', ...) vs. the URL actually named
   'password_reset_confirm').
2. SetNewPasswordAPIView.patch() validated a serializer with no
   token/uidb64 fields and never called .save() - the password was
   never actually changed.
3. The mobile OTP flow (ChangePasswordMobileAPIView) depended on
   settings.OTP_KEY, which didn't exist anywhere.
"""

import pyotp
import pytest
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from django_resaas.engine.core.services.otp_service import _totp_for
from django_resaas.engine.models.user import User
from django_resaas.notifications.enums import Channel
from django_resaas.notifications.providers.fake import FakeProvider
from django_resaas.notifications.providers.registry import NotificationProviderRegistry

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fake_notification_providers():
    """This suite must never send a real email/SMS - swap in Fakes for
    the duration, then restore the real defaults (mirrors
    notifications/tests/conftest.py's own fixture, which only applies
    under notifications/tests/, not here)."""

    email = FakeProvider()
    sms = FakeProvider()

    NotificationProviderRegistry.register(Channel.EMAIL, "django", email, default=True)
    NotificationProviderRegistry.register(Channel.SMS, "twilio", sms, default=True)

    yield {"email": email, "sms": sms}

    NotificationProviderRegistry.unregister_all()
    from django_resaas.notifications.providers import register_default_providers

    register_default_providers()


@pytest.fixture
def client():
    return APIClient()


def _current_otp(identifier):
    return _totp_for(identifier).now()


# =============================================================
# REQUEST OTP
# =============================================================


def test_request_otp_for_fresh_email_sends_code(client, fake_notification_providers):
    response = client.post(
        "/api/register/otp/request/", {"channel": "email", "identifier": "new@example.com"}
    )

    assert response.status_code == 200
    assert len(fake_notification_providers["email"].sent) == 1
    assert fake_notification_providers["email"].sent[0]["recipient"] == "new@example.com"


def test_request_otp_for_fresh_mobile_sends_code(client, fake_notification_providers):
    response = client.post(
        "/api/register/otp/request/", {"channel": "mobile", "identifier": "+258840000000"}
    )

    assert response.status_code == 200
    assert len(fake_notification_providers["sms"].sent) == 1


def test_request_otp_for_already_registered_email_fails(client, fake_notification_providers):
    User.objects.create_user(username="existing", email="taken@example.com", password="x")

    response = client.post(
        "/api/register/otp/request/", {"channel": "email", "identifier": "taken@example.com"}
    )

    assert response.status_code == 400
    assert fake_notification_providers["email"].sent == []


def test_request_otp_for_already_registered_mobile_fails(client, fake_notification_providers):
    User.objects.create_user(
        username="existing2", email=None, mobile="+258840000001", password="x"
    )

    response = client.post(
        "/api/register/otp/request/", {"channel": "mobile", "identifier": "+258840000001"}
    )

    assert response.status_code == 400


def test_request_otp_invalid_channel_rejected(client):
    response = client.post(
        "/api/register/otp/request/", {"channel": "carrier_pigeon", "identifier": "x"}
    )

    assert response.status_code == 400


# =============================================================
# COMPLETE REGISTRATION
# =============================================================


def test_register_with_valid_email_otp_creates_verified_user(client):
    otp = _current_otp("new@example.com")

    response = client.post(
        "/api/register/",
        {
            "username": "newuser",
            "password": "supersecret123",
            "channel": "email",
            "identifier": "new@example.com",
            "otp": otp,
        },
    )

    assert response.status_code == 201, response.data
    user = User.objects.get(email="new@example.com")
    assert user.is_verified_email is True
    assert user.check_password("supersecret123")


def test_register_with_valid_mobile_otp_creates_verified_user(client):
    otp = _current_otp("+258840000002")

    response = client.post(
        "/api/register/",
        {
            "username": "newuser2",
            "password": "supersecret123",
            "channel": "mobile",
            "identifier": "+258840000002",
            "otp": otp,
        },
    )

    assert response.status_code == 201, response.data
    user = User.objects.get(mobile="+258840000002")
    assert user.is_verified_mobile is True


def test_register_with_wrong_otp_fails_and_creates_no_user(client):
    response = client.post(
        "/api/register/",
        {
            "username": "ghostuser",
            "password": "supersecret123",
            "channel": "email",
            "identifier": "ghost@example.com",
            "otp": "000000",
        },
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="ghost@example.com").exists()


def test_register_otp_cannot_be_reused_across_different_identifier(client):
    """The OTP is bound to the identifier it was generated for - one
    request's code must not verify a registration for a different
    email/phone."""

    otp = _current_otp("owner@example.com")

    response = client.post(
        "/api/register/",
        {
            "username": "impostor",
            "password": "supersecret123",
            "channel": "email",
            "identifier": "impostor@example.com",
            "otp": otp,
        },
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="impostor@example.com").exists()


# =============================================================
# PASSWORD RESET BUGS
# =============================================================


def test_request_password_reset_email_does_not_crash(client, fake_notification_providers):
    """Bug #1: reverse('password-reset-confirm', ...) used to raise
    NoReverseMatch for every single request."""

    User.objects.create_user(username="resetme", email="resetme@example.com", password="old")

    response = client.post(
        "/api/password/reset/email/",
        {"email": "resetme@example.com"},
        HTTP_ORIGIN="http://example.test",
    )

    assert response.status_code == 200


def test_request_password_reset_unknown_email_still_returns_200(client):
    """Existence of the email must never be revealed either way."""

    response = client.post(
        "/api/password/reset/email/",
        {"email": "nobody@example.com"},
        HTTP_ORIGIN="http://example.test",
    )

    assert response.status_code == 200


def test_set_new_password_actually_changes_the_password(client):
    """Bug #2: SetNewPasswordAPIView.patch() used to validate and return
    200 without ever calling serializer.save() - the password never
    actually changed."""

    user = User.objects.create_user(username="changeme", email="changeme@example.com", password="old-pass")
    uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
    token = PasswordResetTokenGenerator().make_token(user)

    response = client.patch(
        "/api/password/reset/complete/",
        {"password": "brand-new-pass-123", "uidb64": uidb64, "token": token},
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("brand-new-pass-123") is True
    assert user.check_password("old-pass") is False


def test_set_new_password_rejects_invalid_token(client):
    user = User.objects.create_user(username="changeme2", email="changeme2@example.com", password="old-pass")
    uidb64 = urlsafe_base64_encode(smart_bytes(user.id))

    response = client.patch(
        "/api/password/reset/complete/",
        {"password": "brand-new-pass-123", "uidb64": uidb64, "token": "not-a-real-token"},
        format="json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("old-pass") is True


def test_otp_key_setting_is_configured():
    """Bug #3: settings.OTP_KEY didn't exist, so any OTP flow
    (registration, or the pre-existing mobile password reset) crashed
    with AttributeError the moment it tried to derive a key."""

    from django.conf import settings

    assert getattr(settings, "OTP_KEY", None)


def test_change_password_mobile_hotp_flow_no_longer_crashes_on_otp_key(client):
    """The pre-existing mobile-password-reset OTP flow (HOTP, counter-
    based) only needed OTP_KEY to exist to stop crashing - this doesn't
    re-verify its whole design, just that the missing setting is fixed."""

    import base64

    from django_resaas.engine.core.utils.generate_key_otp import generateKeyOTP

    user = User.objects.create_user(
        username="mobileuser", email=None, mobile="+258840000099", password="old"
    )

    key = base64.b32encode(generateKeyOTP().returnValue("+258840000099").encode())
    otp = pyotp.HOTP(key).at(user.counter)

    response = client.post(
        "/api/password/change/mobile/",
        {"mobile": "+258840000099", "otp": otp, "password": "new-mobile-pass"},
    )

    assert response.status_code == 202
