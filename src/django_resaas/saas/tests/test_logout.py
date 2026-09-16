"""Live bug: every logout failed with "Invalid or expired token", even
with a genuinely valid, unexpired refresh token. Root cause:
LogoutSerializer.save() (saas/data/user/serializers/logout.py) calls
RefreshToken(self.token).blacklist() - a method that only exists on
RefreshToken when `rest_framework_simplejwt.token_blacklist` is in
INSTALLED_APPS (it patches the token classes and provides the
OutstandingToken/BlacklistedToken models the method writes to).
That app was never installed, so blacklist() always raised
AttributeError, silently turned into the misleading "Invalid or
expired token" AuthenticationFailed by the serializer's bare
`except Exception`, regardless of whether the token itself was valid.
Fixed by adding the app to INSTALLED_APPS (dev/settings.py) and
running its migrations."""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


def test_logout_blacklists_a_valid_refresh_token(bootstrap_tenant):
    tenant = bootstrap_tenant("logout-happy-path")
    user = tenant["user"]

    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)

    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post("/api/logout/", {"refresh": str(refresh)}, format="json")

    assert response.status_code == 200
    assert BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()


def test_logout_rejects_a_garbage_refresh_token(bootstrap_tenant):
    tenant = bootstrap_tenant("logout-garbage-token")
    user = tenant["user"]

    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)

    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post("/api/logout/", {"refresh": "not-a-real-token"}, format="json")

    assert response.status_code == 401
