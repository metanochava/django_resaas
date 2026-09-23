"""The RESAAS-context token has its own TTL. The frontend renews it before
it runs out (expires_in) and, as a safety net, after a 403 with exactly
'RESAAS context has expired.' - both halves of that contract are pinned
here so a backend change cannot silently break the silent renewal."""
import pytest
from django.test import override_settings

from django_resaas.saas.core.tenant.context import ResaasContextService

pytestmark = pytest.mark.django_db

CONTEXT_URL = "/api/resaas/context/"


def test_issue_tells_the_client_how_long_the_token_lives(bootstrap_tenant):
    tenant = bootstrap_tenant("context-expires-in")

    response = tenant["client"].post(
        CONTEXT_URL,
        {"entity_id": str(tenant["entity"].id), "branch_id": str(tenant["branch"].id)},
        format="json",
    )

    assert response.status_code == 200, response.data
    assert response.data["token"]
    assert response.data["expires_in"] == ResaasContextService.get_ttl()


@override_settings(RESAAS_CONTEXT_TTL=120)
def test_expires_in_follows_the_configured_ttl(bootstrap_tenant):
    tenant = bootstrap_tenant("context-expires-in-config")

    result = ResaasContextService.issue(
        user=tenant["user"], entity_id=tenant["entity"].id, branch_id=tenant["branch"].id,
    )

    assert result["expires_in"] == 120


def test_an_expired_token_is_a_403_with_the_exact_code_the_frontend_matches(bootstrap_tenant):
    tenant = bootstrap_tenant("context-expired")
    token = tenant["client"]._credentials["HTTP_X_RESAAS_CONTEXT"]

    with override_settings(RESAAS_CONTEXT_TTL=-1):
        response = tenant["client"].get("/api/django_resaas/persons/", HTTP_X_RESAAS_CONTEXT=token)

    assert response.status_code == 403
    # services/contextExpiry.js (quasar_resaas) branches on this exact code -
    # CONTEXT_EXPIRED_CODE - not on the message text.
    assert response.data["error"]["code"] == "resaas_context_expired"
    assert response.data["error"]["message"] == "RESAAS context has expired."


def test_a_fresh_token_is_accepted_after_the_client_renews_it(bootstrap_tenant):
    tenant = bootstrap_tenant("context-renewed")

    renewed = tenant["client"].post(
        CONTEXT_URL,
        {"entity_id": str(tenant["entity"].id), "branch_id": str(tenant["branch"].id)},
        format="json",
    ).data["token"]

    response = tenant["client"].get("/api/django_resaas/persons/", HTTP_X_RESAAS_CONTEXT=renewed)

    assert response.status_code == 200, response.data
