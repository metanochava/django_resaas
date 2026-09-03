"""
Security requirement: an authenticated user's email/mobile can never
change without first proving ownership of the NEW value via OTP -
neither through the dedicated request/confirm-OTP endpoints without a
valid code, nor by bypassing them entirely via a generic PATCH to
/django_resaas/users/{id}/ (UserSerializer makes both fields read-only
there - see serializers/user.py).
"""

import pytest
from rest_framework.test import APIClient

from django_resaas.engine.core.services.otp_service import _totp_for
from django_resaas.engine.models.user import User
from django_resaas.notifications.enums import Channel
from django_resaas.notifications.providers.fake import FakeProvider
from django_resaas.notifications.providers.registry import NotificationProviderRegistry

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fake_notification_providers():
    email = FakeProvider()
    sms = FakeProvider()

    NotificationProviderRegistry.register(Channel.EMAIL, "django", email, default=True)
    NotificationProviderRegistry.register(Channel.SMS, "twilio", sms, default=True)

    yield {"email": email, "sms": sms}

    NotificationProviderRegistry.unregister_all()
    from django_resaas.notifications.providers import register_default_providers

    register_default_providers()


def _current_otp(identifier):
    return _totp_for(identifier).now()


# =============================================================
# GENERIC PATCH CAN NEVER CHANGE EMAIL/MOBILE
# =============================================================


def test_generic_patch_ignores_email_and_mobile(bootstrap_tenant):
    tenant = bootstrap_tenant("contact-user")
    user = tenant["user"]
    original_email = user.email

    response = tenant["client"].patch(
        f"/api/django_resaas/users/{user.id}/",
        {"email": "attacker@example.com", "mobile": "+258849999999", "username": "still-me"},
        format="json",
    )

    assert response.status_code == 200

    user.refresh_from_db()
    assert user.email == original_email
    assert user.mobile is None
    assert user.username == "still-me"


# =============================================================
# REQUEST
# =============================================================


def test_request_contact_otp_requires_auth():
    client = APIClient()

    response = client.post(
        "/api/profile/contact/otp/request/",
        {"channel": "email", "identifier": "new@example.com"},
    )

    assert response.status_code in (401, 403)


def test_request_email_otp_sends_code(bootstrap_tenant, fake_notification_providers):
    tenant = bootstrap_tenant("contact-user2")

    response = tenant["client"].post(
        "/api/profile/contact/otp/request/",
        {"channel": "email", "identifier": "new-email@example.com"},
    )

    assert response.status_code == 200
    assert len(fake_notification_providers["email"].sent) == 1
    assert fake_notification_providers["email"].sent[0]["recipient"] == "new-email@example.com"


def test_request_otp_for_identifier_taken_by_another_user_fails(bootstrap_tenant):
    User.objects.create_user(username="other", email="taken@example.com", password="x")
    tenant = bootstrap_tenant("contact-user3")

    response = tenant["client"].post(
        "/api/profile/contact/otp/request/",
        {"channel": "email", "identifier": "taken@example.com"},
    )

    assert response.status_code == 400


def test_request_otp_for_own_current_email_is_allowed(bootstrap_tenant):
    """Re-requesting/re-confirming your OWN current value must not be
    blocked as "already taken" - the uniqueness check excludes the
    requesting user's own row."""

    tenant = bootstrap_tenant("contact-user4")
    tenant["user"].email = "self@example.com"
    tenant["user"].save(update_fields=["email"])

    response = tenant["client"].post(
        "/api/profile/contact/otp/request/",
        {"channel": "email", "identifier": "self@example.com"},
    )

    assert response.status_code == 200


# =============================================================
# CONFIRM
# =============================================================


def test_confirm_email_otp_with_correct_code_changes_email(bootstrap_tenant):
    tenant = bootstrap_tenant("contact-user5")
    new_email = "confirmed@example.com"

    response = tenant["client"].post(
        "/api/profile/contact/otp/confirm/",
        {"channel": "email", "identifier": new_email, "otp": _current_otp(new_email)},
    )

    assert response.status_code == 200

    tenant["user"].refresh_from_db()
    assert tenant["user"].email == new_email
    assert tenant["user"].is_verified_email is True


def test_confirm_mobile_otp_with_correct_code_changes_mobile(bootstrap_tenant):
    tenant = bootstrap_tenant("contact-user6")
    new_mobile = "+258841234567"

    response = tenant["client"].post(
        "/api/profile/contact/otp/confirm/",
        {"channel": "mobile", "identifier": new_mobile, "otp": _current_otp(new_mobile)},
    )

    assert response.status_code == 200

    tenant["user"].refresh_from_db()
    assert tenant["user"].mobile == new_mobile
    assert tenant["user"].is_verified_mobile is True


def test_confirm_with_wrong_otp_does_not_change_email(bootstrap_tenant):
    tenant = bootstrap_tenant("contact-user7")
    original_email = tenant["user"].email
    new_email = "wrong-otp@example.com"

    response = tenant["client"].post(
        "/api/profile/contact/otp/confirm/",
        {"channel": "email", "identifier": new_email, "otp": "000000"},
    )

    assert response.status_code == 400

    tenant["user"].refresh_from_db()
    assert tenant["user"].email == original_email


def test_confirm_contact_otp_requires_auth():
    client = APIClient()

    response = client.post(
        "/api/profile/contact/otp/confirm/",
        {"channel": "email", "identifier": "x@example.com", "otp": "123456"},
    )

    assert response.status_code in (401, 403)
