"""Forgot my password: password/reset/request/ sends a link or a code to the
account's e-mail or phone (neutral answer, throttled); a code is completed by
password/reset/otp/complete/ (policy, attempt limit, bound to the purpose), a
link by PATCH password/reset/complete/. The link is built only on a trusted
origin (CORS policy / FRONTEND_URL)."""
import re

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from django_resaas.notifications.enums import Channel
from django_resaas.notifications.providers.fake import FakeProvider
from django_resaas.notifications.providers.registry import NotificationProviderRegistry
from django_resaas.saas.core.services.otp_service import OTP_MAX_FAILED_ATTEMPTS, _totp_for
from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db

REQUEST = "/api/password/reset/request/"
OTP_COMPLETE = "/api/password/reset/otp/complete/"
LINK_COMPLETE = "/api/password/reset/complete/"
MOBILE = "+258841234567"
EMAIL = "reset.user@example.com"
OLD = "Old-password-2026!"
STRONG = "Mavuso-2026!river"
TRUSTED = "https://saude.example.test"


@pytest.fixture(autouse=True)
def providers():
    cache.clear()
    email, sms = FakeProvider(), FakeProvider()
    NotificationProviderRegistry.register(Channel.EMAIL, "django", email, default=True)
    NotificationProviderRegistry.register(Channel.SMS, "twilio", sms, default=True)
    yield {"email": email, "sms": sms}
    NotificationProviderRegistry.unregister_all()
    from django_resaas.notifications.providers import register_default_providers

    register_default_providers()
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user():
    user = User.objects.create(username="reset.user", mobile=MOBILE, email=EMAIL)
    user.set_password(OLD)
    user.save()
    return user


def _code(identifier=MOBILE, purpose="password_reset"):
    return _totp_for(identifier, purpose).now()


def _request(client, channel="mobile", identifier=MOBILE, method="otp", origin=TRUSTED):
    return client.post(
        REQUEST, {"channel": channel, "identifier": identifier, "method": method},
        format="json", HTTP_ORIGIN=origin,
    )


def _complete(client, channel="mobile", identifier=MOBILE, otp=None, password=STRONG):
    return client.post(OTP_COMPLETE, {
        "channel": channel, "identifier": identifier, "otp": otp or _code(identifier), "password": password,
    }, format="json")


def _reloaded(user):
    user.refresh_from_db()
    return user


# ------------------------------------------------------------------ request

def test_a_code_by_sms(client, user, providers):
    response = _request(client, identifier="+258 84 123 4567")

    assert response.status_code == 202
    assert response.json()["sent"] is True
    assert providers["sms"].sent[0]["recipient"] == MOBILE
    assert _code() in providers["sms"].sent[0]["body"]


def test_a_code_by_email(client, user, providers):
    _request(client, channel="email", identifier="Reset.User@Example.com")

    assert providers["email"].sent[0]["recipient"] == EMAIL
    assert _code(EMAIL) in providers["email"].sent[0]["body"]


@override_settings(CORS_ALLOWED_ORIGINS=[], CORS_ALLOWED_ORIGIN_REGEXES=[r"^https://.*\.example\.test$"])
def test_a_link_by_sms_and_by_email(client, user, providers):
    _request(client, method="link")
    _request(client, channel="email", identifier=EMAIL, method="link")

    sms_body = providers["sms"].sent[0]["body"]
    assert f"{TRUSTED}/#/auth/resetpassword/" in sms_body
    assert providers["email"].sent[0]["body"].startswith(f"{TRUSTED}/#/auth/resetpassword/")


@override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED], CORS_ALLOWED_ORIGIN_REGEXES=[], FRONTEND_URL="")
def test_an_untrusted_origin_never_builds_a_link(client, user, providers, monkeypatch):
    monkeypatch.delenv("FRONTEND_URL", raising=False)

    response = _request(client, method="link", origin="https://attacker.example")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "reset_link_unavailable"
    assert providers["sms"].sent == []
    # the same answer for a number without an account: no enumeration
    unknown = _request(client, identifier="+258849999999", method="link", origin="https://attacker.example")
    assert unknown.status_code == 503


def test_an_unknown_identifier_gets_the_same_answer_and_nothing_is_sent(client, providers):
    response = _request(client, identifier="+258849999999")

    assert response.status_code == 202
    assert response.json()["sent"] is True
    assert providers["sms"].sent == [] and providers["email"].sent == []


def test_an_invalid_request_uses_the_error_contract(client):
    response = client.post(REQUEST, {"channel": "pigeon", "identifier": "x"}, format="json")

    assert response.status_code == 400
    assert "channel" in response.json()["error"]["details"]


@override_settings(RESAAS_PASSWORD_RESET_OTP_IDENTIFIER_THROTTLE_RATE="2/hour")
def test_sends_to_one_identifier_are_rate_limited(client, user, providers):
    statuses = [_request(client).status_code for _ in range(3)]

    assert statuses == [202, 202, 429]
    assert len(providers["sms"].sent) == 2


# ------------------------------------------------------------------ complete with a code

def test_the_code_resets_the_password(client, user):
    response = _complete(client)

    assert response.status_code == 202, response.content
    assert _reloaded(user).check_password(STRONG) and user.is_verified_mobile


def test_an_email_code_resets_the_password(client, user):
    response = _complete(client, channel="email", identifier=EMAIL)

    assert response.status_code == 202, response.content
    assert _reloaded(user).check_password(STRONG) and user.is_verified_email


def test_a_wrong_code_does_not_reset(client, user):
    response = _complete(client, otp="000000")

    assert response.status_code == 400
    assert "otp" in response.json()["error"]["details"]
    assert _reloaded(user).check_password(OLD)


def test_a_registration_code_cannot_reset_a_password(client, user):
    response = _complete(client, otp=_code(purpose="register"))

    assert response.status_code == 400
    assert _reloaded(user).check_password(OLD)


def test_an_unknown_identifier_fails_like_a_wrong_code(client):
    response = _complete(client, identifier="+258849999999", otp=_code("+258849999999"))

    assert response.status_code == 400
    assert "otp" in response.json()["error"]["details"]


def test_the_password_policy_applies_to_a_code(client, user):
    response = _complete(client, password="123")

    assert response.status_code == 400
    assert "password" in response.json()["error"]["details"]
    assert _reloaded(user).check_password(OLD)


def test_too_many_wrong_codes_lock_the_window(client, user):
    for _ in range(OTP_MAX_FAILED_ATTEMPTS):
        _complete(client, otp="000000")

    response = _complete(client)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "too_many_attempts"
    assert _reloaded(user).check_password(OLD)


# ------------------------------------------------------------------ complete with a link

@override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED])
def test_the_link_resets_the_password_once_and_follows_the_policy(client, user, providers):
    _request(client, method="link")
    uidb64, token = re.search(r"/resetpassword/([^/]+)/([^/\s?]+)", providers["sms"].sent[0]["body"]).groups()

    weak = client.patch(LINK_COMPLETE, {"uidb64": uidb64, "token": token, "password": "123"}, format="json")
    assert weak.status_code == 400

    done = client.patch(LINK_COMPLETE, {"uidb64": uidb64, "token": token, "password": STRONG}, format="json")
    assert done.status_code == 200
    assert _reloaded(user).check_password(STRONG)

    again = client.patch(LINK_COMPLETE, {"uidb64": uidb64, "token": token, "password": "Another-2026!pass"}, format="json")
    assert again.status_code == 400
