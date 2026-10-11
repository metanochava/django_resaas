"""Registration hardening: password policy, username rules, identifier
normalization, OTP attempt limit, rate limits, neutral code request, the
username availability check, an unambiguous login and the error contract.
Registration creates a User only - never Entity / Branch / profile access."""
from unittest import mock

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from django_resaas.saas.core.services.otp_service import OTP_MAX_FAILED_ATTEMPTS, _totp_for
from django_resaas.saas.data.user.serializers.login import authenticate
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.user import User
from django_resaas.notifications.enums import Channel
from django_resaas.notifications.providers.fake import FakeProvider
from django_resaas.notifications.providers.registry import NotificationProviderRegistry

pytestmark = pytest.mark.django_db

REGISTER = "/api/register/"
OTP = "/api/register/otp/request/"
CHECK = "/api/register/username/"
STRONG = "Mavuso-2026!river"


@pytest.fixture(autouse=True)
def fake_providers():
    email, sms = FakeProvider(), FakeProvider()
    NotificationProviderRegistry.register(Channel.EMAIL, "django", email, default=True)
    NotificationProviderRegistry.register(Channel.SMS, "twilio", sms, default=True)
    yield {"email": email, "sms": sms}
    NotificationProviderRegistry.unregister_all()
    from django_resaas.notifications.providers import register_default_providers

    register_default_providers()


@pytest.fixture
def client():
    return APIClient()


def _register(client, *, username="dias.chavana", identifier="dias@example.com", channel="email",
              password=STRONG, otp=None, **extra):
    code = otp if otp is not None else _totp_for(identifier.strip().lower() if channel == "email" else identifier).now()
    return client.post(REGISTER, {
        "username": username, "password": password, "channel": channel,
        "identifier": identifier, "otp": code, **extra,
    }, format="json")


# ------------------------------------------------------------------ creation

def test_a_valid_registration_creates_only_the_user(client):
    response = _register(client, name="Dias Manuel Chavana")

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["username"] == "dias.chavana"
    assert set(body) - {"alerts"} == {"id", "username", "email", "mobile"}
    assert body["alerts"][0]["level"] == "success"
    user = User.objects.get(username="dias.chavana")
    assert user.is_verified_email and user.check_password(STRONG)
    assert (user.person.name, user.person.surname) == ("Dias", "Manuel Chavana")
    # an account is not access
    assert not EntityUser.objects.filter(user=user).exists()
    assert not BranchUserGroup.objects.filter(user=user).exists()
    assert not user.is_staff and not user.is_superuser


def test_privileged_fields_in_the_body_are_ignored(client):
    response = _register(client, is_staff=True, is_superuser=True, entity_id="x", group_id="y", permissions=["add_user"])

    assert response.status_code == 201
    user = User.objects.get(username="dias.chavana")
    assert not user.is_staff and not user.is_superuser
    assert not EntityUser.objects.filter(user=user).exists()


def test_a_weak_password_is_refused_and_creates_nothing(client):
    response = _register(client, password="12345678")

    assert response.status_code == 400
    assert "password" in response.json()["error"]["details"]
    assert not User.objects.filter(username="dias.chavana").exists()


def test_the_email_is_stored_lowercase(client):
    assert _register(client, identifier="Dias@Example.COM").status_code == 201

    assert User.objects.get(username="dias.chavana").email == "dias@example.com"


def test_an_already_registered_identifier_is_refused_after_the_code(client):
    User.objects.create_user(username="first", email="dias@example.com", password="x")

    response = _register(client, identifier="DIAS@example.com")

    assert response.status_code == 400
    assert "identifier" in response.json()["error"]["details"]
    assert User.objects.filter(email__iexact="dias@example.com").count() == 1


# ------------------------------------------------------------------ username rules

@pytest.mark.parametrize("username", ["258840000000", "ab", "1dias", "dias..chavana", "dias.", "dias chavana", "dias@x", "a" * 31])
def test_invalid_usernames_are_refused(client, username):
    response = _register(client, username=username)

    assert response.status_code == 400
    assert "username" in response.json()["error"]["details"]
    assert not User.objects.filter(email="dias@example.com").exists()


def test_the_username_is_stored_lowercase(client):
    assert _register(client, username="Dias.Chavana").status_code == 201

    assert User.objects.filter(username="dias.chavana").exists()


def test_a_taken_username_is_refused_never_silently_changed(client):
    User.objects.create_user(username="dias.chavana", email="other@example.com", password="x")

    response = _register(client, username="DIAS.chavana")

    assert response.status_code == 400
    assert "username" in response.json()["error"]["details"]
    assert not User.objects.filter(email="dias@example.com").exists()


def test_a_concurrent_registration_of_the_same_username_is_a_clean_400(client):
    """Both requests pass validation; the UNIQUE constraint decides at save."""
    User.objects.create_user(username="dias.chavana", email="other@example.com", password="x")

    with mock.patch(
        "django_resaas.saas.data.user.serializers.register.username_is_taken", side_effect=[False, True]
    ):
        response = _register(client)

    assert response.status_code == 400
    assert "username" in response.json()["error"]["details"]
    assert User.objects.filter(username="dias.chavana").count() == 1


# ------------------------------------------------------------------ verification code

def test_a_wrong_code_fails_and_after_the_limit_even_the_right_one_fails(client):
    for _ in range(OTP_MAX_FAILED_ATTEMPTS):
        assert _register(client, otp="000000").status_code == 400

    response = _register(client)  # the right code

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "too_many_attempts"
    assert not User.objects.filter(username="dias.chavana").exists()


def test_a_code_for_one_address_does_not_verify_another(client):
    code = _totp_for("owner@example.com").now()

    response = _register(client, identifier="impostor@example.com", otp=code)

    assert response.status_code == 400
    assert "otp" in response.json()["error"]["details"]


def test_the_code_request_answers_the_same_for_free_and_registered_addresses(client, fake_providers):
    User.objects.create_user(username="first", email="taken@example.com", password="x")

    free = client.post(OTP, {"channel": "email", "identifier": "free@example.com"}, format="json")
    taken = client.post(OTP, {"channel": "email", "identifier": "taken@example.com"}, format="json")

    assert free.status_code == taken.status_code == 202
    assert free.json() == taken.json()
    assert [m["recipient"] for m in fake_providers["email"].sent] == ["free@example.com"]


def test_an_invalid_code_request_uses_the_error_contract(client):
    response = client.post(OTP, {"channel": "pigeon", "identifier": "x"}, format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_identifier"
    assert set(response.json()) == {"error"}


@override_settings(RESAAS_REGISTER_OTP_IDENTIFIER_THROTTLE_RATE="2/hour")
def test_codes_to_one_address_are_rate_limited(client, fake_providers):
    statuses = [
        client.post(OTP, {"channel": "email", "identifier": "flood@example.com"}, format="json").status_code
        for _ in range(3)
    ]

    assert statuses == [202, 202, 429]
    assert len(fake_providers["email"].sent) == 2


@override_settings(RESAAS_REGISTER_THROTTLE_RATE="1/hour")
def test_registration_is_rate_limited(client):
    _register(client, otp="000000")

    assert _register(client, otp="000000").status_code == 429


# ------------------------------------------------------------------ availability

def test_the_availability_check_answers_valid_and_available_only(client):
    User.objects.create_user(username="dias.chavana", email="other@example.com", password="x")

    response = client.get(CHECK, {"candidates": "Dias.Chavana,diaschavana,1bad"})

    assert response.status_code == 200
    assert response.json()["results"] == [
        {"username": "dias.chavana", "valid": True, "available": False},
        {"username": "diaschavana", "valid": True, "available": True},
        {"username": "1bad", "valid": False, "available": False},
    ]
    assert "other@example.com" not in response.content.decode()


def test_the_availability_check_needs_a_name(client):
    response = client.get(CHECK)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "username_required"


@override_settings(RESAAS_USERNAME_CHECK_THROTTLE_RATE="2/hour")
def test_the_availability_check_is_rate_limited(client):
    statuses = [client.get(CHECK, {"candidates": "a.name"}).status_code for _ in range(3)]

    assert statuses == [200, 200, 429]


# ------------------------------------------------------------------ login

def test_login_is_unambiguous_when_a_username_equals_another_users_mobile():
    """Old data may hold a username equal to someone's phone: the phone's
    owner still signs in (mobile is looked up before username), no 500."""
    owner = User.objects.create_user(username="owner", email="owner@example.com", password=STRONG, mobile="258840000000")
    User.objects.create_user(username="258840000000", email="squatter@example.com", password="other-pass-123")

    assert authenticate(value="258840000000", password=STRONG) == owner


def test_login_by_email_ignores_case():
    user = User.objects.create_user(username="caseuser", email="case@example.com", password=STRONG)

    assert authenticate(value="CASE@Example.com", password=STRONG) == user
    assert authenticate(value="caseuser", password=STRONG) == user
    assert authenticate(value="nobody@example.com", password=STRONG) is None
