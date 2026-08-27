"""
`@resaas_action` is a supported extension point (see
docs/development/creating-resource.md) but isn't actually applied to any
real view in this codebase yet - these tests exercise it directly against a
throwaway ViewSet so the mechanism itself stays covered.
"""
import pytest
from django.contrib.auth.models import Permission
from rest_framework.viewsets import ModelViewSet

from dev.demo.models import Product
from dev.demo.serializers import ProductSerializer
from django_resaas.core.decorators.action import resaas_action
from django_resaas.core.services.action_sync_service import ActionSyncService
from django_resaas.models.model_extra_action import ModelExtraAction

pytestmark = pytest.mark.django_db


class _ViewWithArchiveAction(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @resaas_action(detail=True, methods=["post"], label="Archive")
    def archive(self, request, pk=None):
        ...


class _ViewWithNoActions(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


def test_resaas_action_decorator_attaches_metadata():
    method = _ViewWithArchiveAction.archive
    assert method._resaas_action["action"] == "archive"
    assert method._resaas_action["label"] == "Archive"
    assert method._resaas_action["detail"] is True
    assert method._resaas_action["methods"] == ["post"]


def test_sync_view_creates_extra_action_and_permission():
    ActionSyncService.sync_view(_ViewWithArchiveAction)

    extra = ModelExtraAction.objects.get(
        app="demo", model="product", action="archive"
    )
    assert extra.permission == "archive_product"

    assert Permission.objects.filter(codename="archive_product").exists()


def test_sync_view_removes_orphaned_action_when_decorator_is_removed():
    ActionSyncService.sync_view(_ViewWithArchiveAction)
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="archive"
    ).exists()

    # simulate the @resaas_action being removed from the view in code
    ActionSyncService.sync_view(_ViewWithNoActions)

    assert not ModelExtraAction.objects.filter(
        app="demo", model="product", action="archive"
    ).exists()
    assert not Permission.objects.filter(codename="archive_product").exists()
