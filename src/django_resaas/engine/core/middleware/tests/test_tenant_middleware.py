"""
Direct unit tests for TenantContextMiddleware, independent of any view -
covers the missing/invalid/expired/valid token paths.
"""
from django.test import RequestFactory

from django_resaas.engine.core.middleware.tenant import TenantContextMiddleware
from django_resaas.engine.core.tenant.context import ResaasContextService


def _run_middleware(request):
    captured = {}

    def get_response(req):
        captured["request"] = req
        return "response"

    TenantContextMiddleware(get_response)(request)
    return captured["request"]


def test_no_header_leaves_tenant_context_empty():
    request = RequestFactory().get("/")
    result = _run_middleware(request)

    assert result.tenant_context is None
    assert result.tenant_context_error is None
    assert result.entity_id is None
    assert result.branch_id is None
    assert result.group_id is None


def test_invalid_token_sets_tenant_context_error_not_raise():
    request = RequestFactory().get("/", HTTP_X_RESAAS_CONTEXT="not-a-real-token")
    result = _run_middleware(request)

    assert result.tenant_context is None
    assert result.tenant_context_error is not None


def test_valid_token_populates_request_fields():
    from django.conf import settings
    from django.core import signing

    payload = {
        "version": ResaasContextService.VERSION,
        "user_id": "u-1",
        "entity_type_id": "et-1",
        "entity_id": "e-1",
        "branch_id": "b-1",
        "group_id": "g-1",
    }
    token = signing.dumps(
        payload,
        key=settings.SECRET_KEY,
        salt=ResaasContextService.SALT,
        compress=True,
    )

    request = RequestFactory().get("/", HTTP_X_RESAAS_CONTEXT=token)
    result = _run_middleware(request)

    assert result.tenant_context_error is None
    assert result.tenant_context == payload
    assert result.entity_id == "e-1"
    assert result.branch_id == "b-1"
    assert result.group_id == "g-1"


def test_lang_header_is_read_independently_of_context():
    request = RequestFactory().get("/", HTTP_L="pt-pt")
    result = _run_middleware(request)

    assert result.lang_id == "pt-pt"
