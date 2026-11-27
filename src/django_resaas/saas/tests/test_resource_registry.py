"""ResourceRegistry (phase 4): read-only discovery of CRUD resources.

Uses real core models that declare `class RESAAS` (Branch, Entity). Models
without it (Menu) must not be offered as resources.
"""
import pytest

from django_resaas.saas.core.base.registry import VIEW_REGISTRY
from django_resaas.saas.core.services.resource_registry import ResourceRegistry
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.menu import Menu

pytestmark = pytest.mark.django_db


@pytest.fixture
def temp_view():
    """Registers a view for Branch under the core module, removed afterwards."""
    key = "resource_registry_test_branches"
    created = {}

    class _View:
        queryset = Branch.objects.all()

    VIEW_REGISTRY.setdefault("django_resaas", {})[key] = _View
    created[key] = _View
    yield key
    VIEW_REGISTRY["django_resaas"].pop(key, None)


class TestResourceDiscovery:

    def test_declared_crud_models_are_resources(self):
        keys = {info.key for info in ResourceRegistry.resources()}

        assert "django_resaas.branch" in keys
        assert "django_resaas.entity" in keys

    def test_model_without_resaas_is_not_a_resource(self):
        keys = {info.key for info in ResourceRegistry.resources()}

        assert f"{Menu._meta.app_label}.{Menu._meta.model_name}" not in keys

    def test_declared_routes_override_the_defaults(self):
        info = ResourceRegistry.get("django_resaas", "branch")

        assert info.routes["list"] == "list_branch"
        assert info.routes["add"] == "add_branch"

    def test_default_permissions_follow_the_model_name(self):
        info = ResourceRegistry.get("django_resaas", "branch")

        assert info.permissions["view"] == "view_branch"
        assert info.permissions["change"] == "change_branch"

    def test_unknown_model_returns_none(self):
        assert ResourceRegistry.get("django_resaas", "does_not_exist") is None

    def test_discovery_is_sorted_and_stable(self):
        keys = [info.key for info in ResourceRegistry.resources()]

        assert keys == sorted(keys)


class TestBackendEndpoints:

    def test_view_is_linked_to_its_model_by_queryset(self, temp_view):
        info = ResourceRegistry.get("django_resaas", "branch")

        assert temp_view in info.endpoints

    def test_without_registered_view_the_endpoint_list_is_empty_for_that_key(self):
        info = ResourceRegistry.get("django_resaas", "branch")

        assert "resource_registry_test_branches" not in info.endpoints

    def test_resources_without_endpoint_are_reported(self):
        gaps = {info.key for info in ResourceRegistry.without_backend_endpoint()}

        for info in ResourceRegistry.resources():
            assert (info.key in gaps) == (not info.endpoints)
