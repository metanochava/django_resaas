"""
FirebasePushProvider: credentials come from FIREBASE_SERVICE_ACCOUNT_JSON
only, and the RS256 JWT signing step (the one part that genuinely needs
a crypto primitive, via PyJWT+cryptography) must actually work.
"""
import json

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from django_resaas.notifications.exceptions import ProviderConfigurationError
from django_resaas.notifications.providers.firebase import FirebasePushProvider


@pytest.fixture
def fake_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def fake_service_account_json(fake_rsa_key):
    pem = fake_rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    return json.dumps({
        "client_email": "test@example.iam.gserviceaccount.com",
        "private_key": pem,
        "project_id": "test-project",
    })


@pytest.fixture
def provider():
    return FirebasePushProvider()


def test_missing_env_var_raises_configuration_error(provider, monkeypatch):
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)

    with pytest.raises(ProviderConfigurationError):
        provider._service_account()


def test_invalid_json_raises_configuration_error(provider, monkeypatch):
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", "not-json-at-all")

    with pytest.raises(ProviderConfigurationError):
        provider._service_account()


def test_incomplete_service_account_raises_configuration_error(provider, monkeypatch):
    monkeypatch.setenv(
        "FIREBASE_SERVICE_ACCOUNT_JSON",
        json.dumps({"client_email": "x@example.com"}),  # missing private_key/project_id
    )

    with pytest.raises(ProviderConfigurationError):
        provider._service_account()


def test_valid_service_account_is_parsed(provider, monkeypatch, fake_service_account_json):
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", fake_service_account_json)

    account = provider._service_account()

    assert account["project_id"] == "test-project"


def test_access_token_signs_a_verifiable_rs256_jwt(provider, monkeypatch, fake_service_account_json, fake_rsa_key):
    """Exercises the actual crypto path (PyJWT + cryptography) rather
    than mocking it away - this is the part that silently breaks if
    `cryptography` isn't installed."""
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", fake_service_account_json)
    account = provider._service_account()

    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"access_token": "fake-token-123", "expires_in": 3600}).encode()

    def _fake_urlopen(request, timeout=None):
        captured["data"] = request.data
        return _FakeResponse()

    monkeypatch.setattr(
        "django_resaas.notifications.providers.firebase.urllib.request.urlopen",
        _fake_urlopen,
    )

    token = provider._access_token_for(account)

    assert token == "fake-token-123"
    # the assertion sent to Google must be a JWT actually signed with
    # this service account's own key - verify it round-trips.
    import urllib.parse
    form = urllib.parse.parse_qs(captured["data"].decode())
    assertion = form["assertion"][0]
    public_pem = fake_rsa_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    decoded = jwt.decode(
        assertion, public_pem, algorithms=["RS256"], audience="https://oauth2.googleapis.com/token",
    )
    assert decoded["iss"] == account["client_email"]


def test_access_token_is_cached_until_near_expiry(provider, monkeypatch, fake_service_account_json):
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", fake_service_account_json)
    account = provider._service_account()

    calls = {"count": 0}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            calls["count"] += 1
            return json.dumps({"access_token": f"token-{calls['count']}", "expires_in": 3600}).encode()

    monkeypatch.setattr(
        "django_resaas.notifications.providers.firebase.urllib.request.urlopen",
        lambda request, timeout=None: _FakeResponse(),
    )

    first = provider._access_token_for(account)
    second = provider._access_token_for(account)

    assert first == second == "token-1"
    assert calls["count"] == 1


def test_send_posts_to_fcm_with_the_projects_endpoint(provider, monkeypatch, fake_service_account_json):
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", fake_service_account_json)
    monkeypatch.setattr(provider, "_access_token_for", lambda account: "fake-token")

    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"name": "projects/test-project/messages/123"}).encode()

    def _fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode())
        captured["headers"] = request.headers
        return _FakeResponse()

    monkeypatch.setattr(
        "django_resaas.notifications.providers.firebase.urllib.request.urlopen",
        _fake_urlopen,
    )

    result = provider.send(recipient="device-token-abc", subject="Hi", body="Hello there")

    assert result["success"] is True
    assert captured["url"] == "https://fcm.googleapis.com/v1/projects/test-project/messages:send"
    assert captured["body"]["message"]["token"] == "device-token-abc"
    assert captured["body"]["message"]["notification"] == {"title": "Hi", "body": "Hello there"}
    assert captured["headers"]["Authorization"] == "Bearer fake-token"
