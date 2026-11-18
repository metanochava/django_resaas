"""The API authenticates with JWT (Bearer) only. Basic authentication sent a
password on any request - past the login throttle and two-factor - and is
refused even with the right password; so is a Django session cookie."""
import base64

import pytest
from rest_framework.test import APIClient

from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db


def test_basic_authentication_is_refused_even_with_the_right_password():
    User.objects.create_user(username="basic-user", email="basic@example.com", password="right-pass-123")
    credentials = base64.b64encode(b"basic-user:right-pass-123").decode()

    response = APIClient().get("/api/me/", HTTP_AUTHORIZATION=f"Basic {credentials}")

    assert response.status_code == 401


def test_a_session_cookie_does_not_authenticate_the_api(client):
    user = User.objects.create_user(username="session-user", email="session@example.com", password="right-pass-123")
    client.force_login(user)

    assert client.get("/api/me/").status_code == 401
