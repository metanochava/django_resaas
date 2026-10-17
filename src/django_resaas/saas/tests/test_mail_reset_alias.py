"""POST mail/ (deprecated alias of password/reset/email/).

It used to build the reset link from the raw Origin header (a caller could
have a real reset token mailed to a victim, pointing at the caller's host)
and failed with a 500 for every real account while unknown addresses got a
200 (account enumeration). It now runs the password/reset/email/ flow.
"""
import pytest
from rest_framework.test import APIClient

from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "django.core.mail.EmailMultiAlternatives.send",
        lambda self, *a, **k: sent.append({"to": self.to, "html": self.alternatives[0][0]}),
    )
    return sent


@pytest.fixture
def trusted(settings):
    settings.FRONTEND_URL = "https://app.mail.test"
    settings.CORS_ALLOWED_ORIGINS = ["https://app.mail.test"]
    settings.CORS_ALLOWED_ORIGIN_REGEXES = []
    settings.CORS_ORIGIN_ALLOW_ALL = False


def test_untrusted_origin_never_reaches_the_link(trusted, outbox):
    User.objects.create_user(username="victim", email="victim@mail.test", password="Own-Password-1")

    response = APIClient().post(
        "/api/mail/", {"email": "victim@mail.test"}, format="json", HTTP_ORIGIN="https://evil.example",
    )

    assert response.status_code == 202
    assert len(outbox) == 1
    assert "evil.example" not in outbox[0]["html"]
    assert "https://app.mail.test/#/auth/resetpassword/" in outbox[0]["html"]


def test_known_and_unknown_addresses_get_the_same_answer(trusted, outbox):
    User.objects.create_user(username="known", email="known@mail.test", password="Own-Password-1")
    client = APIClient()

    known = client.post("/api/mail/", {"email": "known@mail.test"}, format="json")
    unknown = client.post("/api/mail/", {"email": "nobody@mail.test"}, format="json")

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert [item["to"] for item in outbox] == [["known@mail.test"]]


def test_without_a_trusted_origin_nothing_is_sent(settings, outbox):
    settings.FRONTEND_URL = ""
    settings.CORS_ALLOWED_ORIGINS = []
    settings.CORS_ALLOWED_ORIGIN_REGEXES = []
    User.objects.create_user(username="nolink", email="nolink@mail.test", password="Own-Password-1")

    response = APIClient().post(
        "/api/mail/", {"email": "nolink@mail.test"}, format="json", HTTP_ORIGIN="https://evil.example",
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "reset_link_unavailable"
    assert outbox == []


def test_missing_email_is_400(trusted):
    assert APIClient().post("/api/mail/", {}, format="json").status_code == 400
