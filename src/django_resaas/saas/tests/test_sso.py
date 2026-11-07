"""Single sign-on between frontend domains: a single-use code (PKCE S256,
bound to its redirect_uri, trusted origins only) carries a session from one
domain to another and becomes a NEW session there."""
import secrets
import threading
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from django_resaas.saas.core.services import sso_service
from django_resaas.saas.models.audit_log import AuditLog
from django_resaas.saas.models.sso_authorization_code import SsoAuthorizationCode
from django_resaas.saas.models.user import User
from django_resaas.saas.models.user_login import UserLogin

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("_trusted_origins"),
]

PASSWORD = "Own-Password-1"
CALLBACK = "https://docodela.co.mz/#/sso/callback"


@pytest.fixture
def _trusted_origins():
    cache.clear()
    with override_settings(
        CORS_ORIGIN_ALLOW_ALL=False,
        CORS_ALLOWED_ORIGINS=["https://docodela.co.mz", "https://auth.mytech.co.mz"],
        CORS_ALLOWED_ORIGIN_REGEXES=[r"^https://([a-z0-9-]+\.)?dev\.mytech\.co\.mz$"],
    ):
        yield
    cache.clear()


def _account(username="ana"):
    user = User.objects.create_user(username=username, email=f"{username}@sso.test", password=PASSWORD)
    User.objects.filter(pk=user.pk).update(is_verified_email=True)
    return user


def _sign_in(user):
    response = APIClient().post("/api/login/", {"identifier": user.username, "password": PASSWORD}, format="json")
    assert response.status_code == 202, response.data
    client = APIClient(raise_request_exception=False)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['tokens']['access']}")
    client.refresh = response.data["tokens"]["refresh"]
    return client


def _pkce():
    verifier = secrets.token_urlsafe(48)
    return verifier, sso_service.challenge_for(verifier)


def _code(client, redirect_uri=CALLBACK):
    verifier, challenge = _pkce()
    response = client.post("/api/sso/code/", {"redirect_uri": redirect_uri, "code_challenge": challenge}, format="json")
    return response, verifier


def _exchange(code, verifier, redirect_uri=CALLBACK):
    return APIClient(raise_request_exception=False).post(
        "/api/sso/token/", {"code": code, "code_verifier": verifier, "redirect_uri": redirect_uri}, format="json"
    )


class TestHappyPath:
    def test_a_session_on_one_domain_becomes_a_new_session_on_another(self):
        user = _account()
        client = _sign_in(user)

        issued, verifier = _code(client)
        assert issued.status_code == 202, issued.data
        assert issued.data["expires_in"] == sso_service.CODE_TTL

        exchanged = _exchange(issued.data["code"], verifier)
        assert exchanged.status_code == 202, exchanged.data
        assert exchanged.data["id"] == user.id
        assert exchanged.data["tokens"]["access"] and exchanged.data["tokens"]["refresh"]

        # a distinct session, listed like any other sign-in
        assert UserLogin.objects.filter(user=user).count() == 2
        assert client.refresh != exchanged.data["tokens"]["refresh"]

        # the new access token works on its own
        other = APIClient()
        other.credentials(HTTP_AUTHORIZATION=f"Bearer {exchanged.data['tokens']['access']}")
        assert other.get("/api/sessions/").status_code == 200

        assert AuditLog.objects.filter(action=sso_service.SIGN_IN, object_id=str(user.pk)).exists()

    def test_only_the_hash_of_the_code_is_stored(self):
        issued, _ = _code(_sign_in(_account()))
        row = SsoAuthorizationCode.objects.get()
        assert issued.data["code"] not in (row.code_hash, row.redirect_uri, row.code_challenge)

    def test_a_regex_trusted_origin_is_accepted(self):
        issued, verifier = _code(_sign_in(_account()), "https://farmacia.dev.mytech.co.mz/#/sso/callback")
        assert issued.status_code == 202, issued.data


class TestIssuing:
    def test_without_a_session_there_is_no_code(self):
        _, challenge = _pkce()
        response = APIClient().post("/api/sso/code/", {"redirect_uri": CALLBACK, "code_challenge": challenge}, format="json")
        assert response.status_code == 401
        assert not SsoAuthorizationCode.objects.exists()

    @pytest.mark.parametrize(
        "redirect_uri",
        [
            "https://evil.example/#/sso/callback",
            "https://docodela.co.mz.evil.example/#/sso/callback",
            "https://user:pass@docodela.co.mz/#/sso/callback",
            "javascript:alert(1)",
            "//docodela.co.mz/#/sso/callback",
            "",
        ],
    )
    def test_an_untrusted_redirect_is_refused(self, redirect_uri):
        response, _ = _code(_sign_in(_account()), redirect_uri)
        assert response.status_code == 400
        assert response.data["error"]["code"] == "sso_invalid_redirect"
        assert not SsoAuthorizationCode.objects.exists()

    def test_a_malformed_challenge_is_refused(self):
        response = _sign_in(_account()).post(
            "/api/sso/code/", {"redirect_uri": CALLBACK, "code_challenge": "short"}, format="json"
        )
        assert response.status_code == 400
        assert response.data["error"]["code"] == "sso_invalid_request"

    @override_settings(CORS_ORIGIN_ALLOW_ALL=True)
    def test_allow_all_cors_trusts_no_redirect(self):
        response, _ = _code(_sign_in(_account()))
        assert response.status_code == 400


class TestRedeeming:
    def test_the_code_works_once(self):
        issued, verifier = _code(_sign_in(_account()))
        assert _exchange(issued.data["code"], verifier).status_code == 202
        again = _exchange(issued.data["code"], verifier)
        assert again.status_code == 401
        assert again.data["error"]["code"] == "sso_code_invalid"

    def test_a_wrong_verifier_fails_and_spends_the_code(self):
        issued, verifier = _code(_sign_in(_account()))
        wrong, _ = _pkce()
        assert _exchange(issued.data["code"], wrong).status_code == 401
        # the right verifier afterwards is too late: the first try spent it
        assert _exchange(issued.data["code"], verifier).status_code == 401

    def test_a_different_redirect_uri_fails(self):
        issued, verifier = _code(_sign_in(_account()))
        assert _exchange(issued.data["code"], verifier, "https://auth.mytech.co.mz/#/sso/callback").status_code == 401

    def test_an_expired_code_fails(self):
        issued, verifier = _code(_sign_in(_account()))
        SsoAuthorizationCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        assert _exchange(issued.data["code"], verifier).status_code == 401

    def test_an_unknown_code_fails(self):
        verifier, _ = _pkce()
        assert _exchange("not-a-code", verifier).status_code == 401

    def test_an_inactive_user_gets_no_session(self):
        user = _account()
        issued, verifier = _code(_sign_in(user))
        User.objects.filter(pk=user.pk).update(is_active=False)
        assert _exchange(issued.data["code"], verifier).status_code == 401

    def test_ending_the_source_session_kills_its_pending_codes(self):
        user = _account()
        client = _sign_in(user)
        issued, verifier = _code(client)

        from rest_framework_simplejwt.tokens import RefreshToken

        RefreshToken(client.refresh).blacklist()
        assert _exchange(issued.data["code"], verifier).status_code == 401
        assert UserLogin.objects.filter(user=user).count() == 1

    @pytest.mark.parametrize("payload", [{}, {"code": 1, "code_verifier": [], "redirect_uri": None}])
    def test_malformed_requests_get_the_same_answer(self, payload):
        response = APIClient().post("/api/sso/token/", payload, format="json")
        assert response.status_code == 401
        assert response.data["error"]["code"] == "sso_code_invalid"

    @pytest.mark.django_db(transaction=True)
    def test_two_simultaneous_exchanges_mint_one_session(self):
        if connection.vendor == "sqlite":
            pytest.skip("row locks need a server database")
        user = _account()
        issued, verifier = _code(_sign_in(user))
        statuses = []

        def exchange():
            statuses.append(_exchange(issued.data["code"], verifier).status_code)
            connection.close()

        threads = [threading.Thread(target=exchange) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert sorted(statuses) == [202, 401]
        assert UserLogin.objects.filter(user=user).count() == 2


class TestRedirectCheck:
    def test_a_trusted_redirect_is_confirmed(self):
        response = APIClient().get("/api/sso/redirect_check/", {"redirect_uri": CALLBACK})
        assert response.status_code == 200
        assert response.data["allowed"] is True

    @pytest.mark.parametrize("redirect_uri", ["https://evil.example/#/sso/callback", ""])
    def test_an_untrusted_redirect_is_refused(self, redirect_uri):
        response = APIClient().get("/api/sso/redirect_check/", {"redirect_uri": redirect_uri})
        assert response.status_code == 400
        assert response.data["error"]["code"] == "sso_invalid_redirect"
