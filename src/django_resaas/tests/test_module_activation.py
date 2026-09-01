"""
FASE 1 - P0.5: module activation (EntityApp) is enforced in the backend,
per-tenant - not just hidden in the frontend menu.

Uses the real "demo" module/app (see BootstrapService/conftest.py's
bootstrap_tenant, which only activates "hr" by default - "demo" has to be
requested explicitly via modules=("demo",), exactly like activating any
other optional module for a real tenant).
"""
import pytest

pytestmark = pytest.mark.django_db


def test_request_is_allowed_when_the_module_is_active(bootstrap_tenant):
    tenant = bootstrap_tenant("module-active-tenant", modules=("demo",))

    response = tenant["client"].get("/api/demo/products/")
    assert response.status_code == 200


def test_request_is_denied_when_the_module_is_not_active(bootstrap_tenant):
    # deliberately no modules=("demo",) - the "demo" module was never
    # activated for this tenant
    tenant = bootstrap_tenant("module-inactive-tenant")

    response = tenant["client"].get("/api/demo/products/")
    assert response.status_code == 403


def test_module_activation_does_not_leak_between_entities(bootstrap_tenant):
    """
    Entity A has the module active, Entity B does not - A's activation
    must never leak into B's request, even though both requests hit the
    exact same endpoint.
    """
    tenant_a = bootstrap_tenant("module-leak-tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("module-leak-tenant-b")  # no "demo"

    response_a = tenant_a["client"].get("/api/demo/products/")
    assert response_a.status_code == 200

    response_b = tenant_b["client"].get("/api/demo/products/")
    assert response_b.status_code == 403
