"""
Executable proof of the "complete flow" this demo app exists for:

    model (Product) -> BaseSerializer -> BaseAPIView -> real HTTP request
    -> multi-tenant + RBAC enforcement -> ResaasSchemaBuilder response

using nothing but the same public patterns documented in
docs/development/creating-resource.md and docs/api/schema-contract.md.

The tenant/RBAC bootstrap below mirrors what `manage.py create_entity`
does interactively (BootstrapService + the permission-creation signal in
core/signals/permissions.py), done here non-interactively so it can run
in CI.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django_resaas.core.services.bootstrap_service import BootstrapService
from django_resaas.core.signals.permissions import create_model_permissions
from django_resaas.core.tenant.context import ResaasContextService
from django_resaas.models.app import App
from django_resaas.models.branch_user_group import BranchUserGroup
from django_resaas.models.entity_app import EntityApp
from django_resaas.models.group import Group

User = get_user_model()

pytestmark = pytest.mark.django_db


class _FakeAppConfig:
    """Minics the `app_config` kwarg django.setup()'s post_migrate signal
    passes - see core/signals/permissions.create_model_permissions, which
    only acts when `app_config.name == "django_resaas"`."""

    name = "django_resaas"


@pytest.fixture
def tenant_client():
    user = User.objects.create_user(
        username="demo-user",
        email="demo-user@example.com",
        password="demo-pass-123",
    )

    bootstrap = BootstrapService.run(
        entity_type="Demo Type",
        entity="Demo Tenant",
        branch="Main",
        user=user,
        group="Admin",
    )
    entity = bootstrap["entity"]
    branch = bootstrap["branch"]

    # The permission-creation signal (core/signals/permissions.py) no-ops
    # until an EntityType exists, which is why it's re-run here explicitly
    # rather than relying on the one that fired during test-DB migration.
    create_model_permissions(sender=None, app_config=_FakeAppConfig())

    root_group = Group.objects.get(name="Root")
    BranchUserGroup.objects.get_or_create(
        user=user,
        branch=branch,
        group=root_group,
        defaults={"state": 1},
    )

    # BootstrapService only activates the "hr" module for the new entity;
    # this demo app is its own per-client module (see dev/demo/views.py's
    # @registerView(module="demo")) and must be activated the same way a
    # real deployment would activate any optional module for a tenant.
    demo_app, _ = App.objects.get_or_create(
        name="demo",
        defaults={"state": "Active"},
    )
    EntityApp.objects.get_or_create(
        entity=entity,
        app=demo_app,
        defaults={"state": "Active"},
    )

    context = ResaasContextService.issue(
        user=user,
        entity_id=entity.id,
        branch_id=branch.id,
        group_id=root_group.id,
    )

    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(
        HTTP_X_RESAAS_CONTEXT=context["token"],
        # `check_permission` (core/base/permissions.py) requires a truthy
        # language id on every request, independent of the RESAAS context.
        HTTP_L="1",
    )

    return client


def test_full_crud_flow(tenant_client):
    # list: starts empty
    response = tenant_client.get("/api/demo/products/")
    assert response.status_code == 200
    assert response.data["results"] == []

    # create
    response = tenant_client.post(
        "/api/demo/products/",
        {"name": "Widget", "sku": "WID-1", "price": "9.99"},
    )
    assert response.status_code == 201
    product_id = response.data["id"]

    # list: contains the new product, tenant fields auto-filled
    response = tenant_client.get("/api/demo/products/")
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "Widget"

    # retrieve
    response = tenant_client.get(f"/api/demo/products/{product_id}/")
    assert response.status_code == 200
    assert response.data["sku"] == "WID-1"

    # update
    response = tenant_client.patch(
        f"/api/demo/products/{product_id}/", {"price": "12.50"}
    )
    assert response.status_code == 200
    assert response.data["price"] == "12.50"

    # soft delete: disappears from the default list...
    response = tenant_client.delete(f"/api/demo/products/{product_id}/")
    assert response.status_code == 204
    response = tenant_client.get("/api/demo/products/")
    assert response.data["count"] == 0

    # ...but is still there via ?objects=all, and can be restored
    response = tenant_client.get("/api/demo/products/?objects=all")
    assert response.data["count"] == 1
    response = tenant_client.post(f"/api/demo/products/{product_id}/restore/")
    assert response.status_code == 200
    response = tenant_client.get("/api/demo/products/")
    assert response.data["count"] == 1


def test_search(tenant_client):
    tenant_client.post(
        "/api/demo/products/", {"name": "Widget", "sku": "WID-1", "price": "9.99"}
    )
    tenant_client.post(
        "/api/demo/products/", {"name": "Gadget", "sku": "GAD-1", "price": "5.00"}
    )

    response = tenant_client.get("/api/demo/products/?search=widget")
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "Widget"


def test_schema_endpoint_matches_the_documented_contract(tenant_client):
    response = tenant_client.get("/api/django_resaas/resaasapps/demo/product/schema/")
    assert response.status_code == 200

    assert response.data["schema_version"] == "1.0"
    assert response.data["model"]["app"] == "demo"
    assert response.data["model"]["name"] == "product"
    assert response.data["model"]["endpoint"] == "demo/products/"
    assert response.data["ui"]["icon"] == "mdi-package-variant"
    assert response.data["filters"]["search_fields"] == ["name", "sku"]
