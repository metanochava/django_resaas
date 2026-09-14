"""`manage.py grant_root_action_permissions` - the missing "assign to
Root" step ActionSyncService deliberately never does on its own (see
the command's own help text and core/services/action_sync_service.py).

Same throwaway-ViewSet-against-dev.demo.Product pattern as
test_resaas_commands.py/test_action_sync.py, plus the same
VIEW_REGISTRY-swapping fixture - these commands import VIEW_REGISTRY by
reference, so mutating it in place is visible to them without patching
imports in the command module."""
import pytest
from django.contrib.auth.models import Permission
from django.core.management import call_command
from rest_framework.viewsets import ModelViewSet

from dev.demo.models import Product
from dev.demo.serializers import ProductSerializer
from django_resaas.saas.core.base.registry import VIEW_REGISTRY
from django_resaas.saas.core.decorators.action import resaas_action
from django_resaas.saas.models.group import Group
from django_resaas.saas.models.model_extra_action import ManagedBy, ModelExtraAction

pytestmark = pytest.mark.django_db


class _ViewWithShipAction(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @resaas_action(detail=True, methods=["post"], label="Ship")
    def ship(self, request, pk=None):
        ...


@pytest.fixture
def clean_registry():
    saved = {key: dict(value) for key, value in VIEW_REGISTRY.items()}
    VIEW_REGISTRY.clear()
    try:
        yield VIEW_REGISTRY
    finally:
        VIEW_REGISTRY.clear()
        VIEW_REGISTRY.update(saved)


class TestGrantRootActionPermissions:

    def test_grants_a_synced_action_permission_to_root(self, clean_registry):
        clean_registry["demo"] = {"product": _ViewWithShipAction}

        call_command("grant_root_action_permissions")

        root_group = Group.objects.get(name="Root")
        assert root_group.permissions.filter(codename="ship_product").exists()

    def test_does_not_touch_manually_managed_permissions(self, clean_registry, django_user_model):
        """A ModelExtraAction a human curated by hand (managed_by=MANUAL)
        is never RESAAS's to grant - only decorator-managed ones."""
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(Product)
        Permission.objects.get_or_create(
            content_type=ct, codename="hand_curated_product",
            defaults={"name": "Hand curated"},
        )
        ModelExtraAction.objects.create(
            app="demo", model="product", action="hand_curated",
            permission="hand_curated_product", managed_by=ManagedBy.MANUAL,
        )

        call_command("grant_root_action_permissions")

        root_group, _ = Group.objects.get_or_create(name="Root")
        assert not root_group.permissions.filter(codename="hand_curated_product").exists()

    def test_is_idempotent(self, clean_registry):
        clean_registry["demo"] = {"product": _ViewWithShipAction}

        call_command("grant_root_action_permissions")
        call_command("grant_root_action_permissions")

        root_group = Group.objects.get(name="Root")
        assert root_group.permissions.filter(codename="ship_product").count() == 1

    def test_empty_registry_still_grants_previously_synced_permissions(self, clean_registry):
        """VIEW_REGISTRY being empty in *this* process (e.g. a management
        shell that never resolved a URL) must not stop the command from
        granting permissions a previous sync already created."""
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(Product)
        Permission.objects.get_or_create(
            content_type=ct, codename="ship_product",
            defaults={"name": "Can ship product"},
        )
        ModelExtraAction.objects.create(
            app="demo", model="product", action="ship",
            permission="ship_product", managed_by=ManagedBy.DECORATOR,
        )

        call_command("grant_root_action_permissions")

        root_group = Group.objects.get(name="Root")
        assert root_group.permissions.filter(codename="ship_product").exists()
