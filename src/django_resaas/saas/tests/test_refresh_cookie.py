"""The refresh token in an HttpOnly cookie for the frontends of the API's own
site (core/services/refresh_cookie.py, RESAAS_REFRESH_COOKIE_SITES).

- A sign-in from venda.mytech.co.mz to app.mytech.co.mz: the refresh token
  is in an HttpOnly, Secure, SameSite=Lax cookie on the API path, never in
  the body; the body says until when it lives.
- Refresh and logout read the cookie when the body has none; logout clears
  it; the cookie is ignored for a request of another Origin (CSRF).
- Another site (an own domain) keeps the refresh token in the body."""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from django_resaas.saas.models.user import User

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("cookie_sites"),
]

API_HOST = "app.mytech.co.mz"
SAME_SITE = "https://venda.mytech.co.mz"
OWN_DOMAIN = "https://clinicaamal.co.mz"
PASSWORD = "Pass-12345-xyz"


@pytest.fixture
def cookie_sites():
    with override_settings(RESAAS_REFRESH_COOKIE_SITES=["mytech.co.mz"], ALLOWED_HOSTS=["*"]):
        yield


def _client(origin):
    return APIClient(HTTP_HOST=API_HOST, HTTP_ORIGIN=origin)


def _login(client, username):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password=PASSWORD)
    User.objects.filter(pk=user.pk).update(is_verified_email=True)
    response = client.post("/api/login/", {"identifier": username, "password": PASSWORD}, format="json")
    assert response.status_code in (200, 202), response.content
    return response


def test_a_same_site_sign_in_puts_the_refresh_in_an_httponly_cookie():
    client = _client(SAME_SITE)
    response = _login(client, "cookie-login")

    assert "refresh" not in response.data["tokens"]
    assert response.data["tokens"]["access"]
    assert response.data["refresh_cookie"]["expires_at"]
    cookie = response.cookies["resaas_refresh"]
    assert cookie.value
    assert cookie["httponly"] and cookie["secure"]
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == "/api/"


def test_the_cookie_refreshes_and_rotates_without_a_body():
    client = _client(SAME_SITE)
    first = _login(client, "cookie-refresh").cookies["resaas_refresh"].value

    response = client.post("/api/refresh_token/", {}, format="json")

    assert response.status_code in (200, 202), response.content
    assert response.data["access"]
    assert "refresh" not in response.data
    assert response.cookies["resaas_refresh"].value != first          # rotated, in the cookie


def test_the_cookie_is_ignored_for_another_origin():
    client = _client(SAME_SITE)
    refresh = _login(client, "cookie-csrf").cookies["resaas_refresh"].value

    foreign = _client("https://evil.example.com")
    foreign.cookies["resaas_refresh"] = refresh
    assert foreign.post("/api/refresh_token/", {}, format="json").status_code in (400, 401)


def test_logout_reads_and_clears_the_cookie():
    client = _client(SAME_SITE)
    login = _login(client, "cookie-logout")
    refresh = login.cookies["resaas_refresh"].value
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['tokens']['access']}")

    response = client.post("/api/logout/", {}, format="json")

    assert response.status_code in (200, 202), response.content
    assert response.cookies["resaas_refresh"]["max-age"] == 0                        # cleared
    assert client.post("/api/refresh_token/", {"refresh": refresh}, format="json").status_code == 401   # ended


def test_an_own_domain_keeps_the_refresh_in_the_body():
    response = _login(_client(OWN_DOMAIN), "cookie-own-domain")

    assert response.data["tokens"]["refresh"]
    assert "resaas_refresh" not in response.cookies
    assert "refresh_cookie" not in response.data
