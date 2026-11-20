"""schema.operations: the writes a model's API accepts (its registered views'
http_method_names), so the frontend offers no Add/Edit/Delete for a
read-only endpoint."""
import pytest

from django_resaas.saas.core.base.registry import VIEW_REGISTRY
from django_resaas.saas.core.schema import ResaasSchemaBuilder
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.printer import Printer

pytestmark = pytest.mark.django_db


def test_a_full_crud_endpoint_accepts_every_write():
    assert ResaasSchemaBuilder(Model=Branch).build_operations() == {"create": True, "update": True, "delete": True}


def test_a_read_only_endpoint_says_so(monkeypatch):
    class ReadOnlyPrinters:
        queryset = Printer.objects.all()
        http_method_names = ["get", "head", "options"]

    # the model's only registered view is read-only
    registry = {module: {k: v for k, v in views.items() if getattr(getattr(v, "queryset", None), "model", None) is not Printer}
                for module, views in VIEW_REGISTRY.items()}
    registry["tests"] = {"printers": ReadOnlyPrinters}
    monkeypatch.setattr("django_resaas.saas.core.base.registry.VIEW_REGISTRY", registry)

    assert ResaasSchemaBuilder(Model=Printer).build_operations() == {"create": False, "update": False, "delete": False}


def test_the_schema_endpoint_carries_operations(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-ops")

    response = tenant["client"].get("/api/django_resaas/resaasapps/django_resaas/branch/schema/")

    data = response.data.get("data", response.data)
    assert response.status_code == 200
    assert data["operations"] == {"create": True, "update": True, "delete": True}
