"""/api/me/ reports the account's own e-mail/mobile verification state, so the
Account Center can show "verified" as a fact instead of guessing it."""
import pytest

from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db


def test_me_exposes_the_verification_flags(bootstrap_tenant):
    tenant = bootstrap_tenant("me-verified")
    # the client is force-authenticated with THIS instance
    tenant["user"].is_verified_email = True
    tenant["user"].save(update_fields=["is_verified_email"])

    response = tenant["client"].get("/api/me/")

    assert response.status_code == 200
    assert response.data["is_verified_email"] is True
    assert response.data["is_verified_mobile"] is False


def test_the_flags_cannot_be_written_through_me(bootstrap_tenant):
    tenant = bootstrap_tenant("me-readonly")

    tenant["client"].patch("/api/me/", {"is_verified_email": True}, format="json")

    assert User.objects.get(pk=tenant["user"].pk).is_verified_email is False
