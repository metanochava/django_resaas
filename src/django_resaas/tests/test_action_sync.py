"""
FASE 1 - P0.3: ActionSyncService / @resaas_action sync mechanics.

Permission ownership/lifecycle (managed_by, permission_managed, explicit
permission=, manual-vs-decorator collisions) lives in test_permissions.py
instead - this file is about action discovery and the sync/orphan-removal
mechanics themselves.

`@resaas_action` isn't actually applied to any real view in this codebase
yet (see docs/development/creating-resource.md) - these tests exercise it
directly against throwaway ViewSets so the mechanism itself stays covered.
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


# =========================================================
# ACTION SIMPLES
# =========================================================

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


def test_sync_view_alone_never_removes_orphans():
    """
    sync_view() only upserts what IS declared on the view passed in - it
    must never delete anything, since it has no way of knowing whether
    some other view of the same model still declares an action it
    doesn't see here.
    """
    ActionSyncService.sync_view(_ViewWithArchiveAction)
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="archive"
    ).exists()

    # a view with no actions must NOT be treated as "archive was removed"
    ActionSyncService.sync_view(_ViewWithNoActions)

    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="archive"
    ).exists()
    assert Permission.objects.filter(codename="archive_product").exists()


# =========================================================
# ACTIONS HERDADAS / OVERRIDE
# =========================================================

class _PaymentMixin:
    @resaas_action(detail=True, methods=["post"], label="Pay")
    def pay(self, request, pk=None):
        ...


class _ViewInheritingAction(_PaymentMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class _ViewOverridingInheritedAction(_PaymentMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @resaas_action(detail=True, methods=["post"], label="Pay (overridden)")
    def pay(self, request, pk=None):
        ...


class _ViewOverridingInheritedActionWithoutDecorator(_PaymentMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # deliberately overrides the mixin's @resaas_action "pay" with a plain
    # method - this subclass no longer wants it to be a RESAAS action
    def pay(self, request, pk=None):
        ...


def test_action_inherited_from_a_mixin_is_discovered():
    ActionSyncService.sync_view(_ViewInheritingAction)

    extra = ModelExtraAction.objects.get(app="demo", model="product", action="pay")
    assert extra.label == "Pay"


def test_subclass_override_of_an_inherited_action_wins():
    ActionSyncService.sync_view(_ViewOverridingInheritedAction)

    extra = ModelExtraAction.objects.get(app="demo", model="product", action="pay")
    assert extra.label == "Pay (overridden)"

    # no duplicate row was created for the same identity
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="pay"
    ).count() == 1


def test_subclass_override_without_the_decorator_is_not_discovered():
    """
    inspect.getmembers(cls) resolves each attribute name via normal
    Python attribute lookup, which follows the MRO - so a subclass
    overriding an inherited @resaas_action with a plain (undecorated)
    method means that name no longer carries `_resaas_action` metadata
    at all. _get_declared_actions() must not discover it here.
    """
    declared = ActionSyncService._get_declared_actions(
        _ViewOverridingInheritedActionWithoutDecorator
    )
    assert declared == []


# =========================================================
# DUAS VIEWS PARA O MESMO MODEL
# =========================================================

class _TriageView(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @resaas_action(detail=True, methods=["post"], label="Triage")
    def triage(self, request, pk=None):
        ...


class _DischargeView(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @resaas_action(detail=True, methods=["post"], label="Discharge")
    def discharge(self, request, pk=None):
        ...


def test_sync_view_does_not_remove_actions_from_another_view():
    """
    The exact regression this protects against: syncing view A, then
    separately syncing view B (of the SAME model) must never delete
    view A's action - sync_view(ViewB) has no business touching
    anything it didn't itself declare.
    """
    ActionSyncService.sync_view(_TriageView)
    ActionSyncService.sync_view(_DischargeView)

    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="triage"
    ).exists()
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="discharge"
    ).exists()


def test_sync_registry_aggregates_actions_from_multiple_views_before_removing_orphans():
    registry = {
        "demo": {
            "triage": _TriageView,
            "discharge": _DischargeView,
        }
    }

    ActionSyncService.sync_registry(registry)

    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="triage"
    ).exists()
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="discharge"
    ).exists()


def test_sync_registry_still_removes_a_true_orphan_across_views():
    registry_with_both = {
        "demo": {"triage": _TriageView, "discharge": _DischargeView}
    }
    ActionSyncService.sync_registry(registry_with_both)

    # simulate "discharge" view being removed from the codebase entirely
    registry_without_discharge = {"demo": {"triage": _TriageView}}
    ActionSyncService.sync_registry(registry_without_discharge)

    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="triage"
    ).exists()
    assert not ModelExtraAction.objects.filter(
        app="demo", model="product", action="discharge"
    ).exists()
    assert not Permission.objects.filter(codename="discharge_product").exists()


# =========================================================
# REMOÇÃO DE DECORATOR ACTION
# =========================================================

def test_sync_registry_removes_action_when_decorator_is_removed_from_code():
    registry_with_action = {"demo": {"archive": _ViewWithArchiveAction}}
    ActionSyncService.sync_registry(registry_with_action)
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="archive"
    ).exists()

    # simulate the @resaas_action being removed from the view in code
    registry_without_action = {"demo": {"archive": _ViewWithNoActions}}
    ActionSyncService.sync_registry(registry_without_action)

    assert not ModelExtraAction.objects.filter(
        app="demo", model="product", action="archive"
    ).exists()
    assert not Permission.objects.filter(codename="archive_product").exists()
