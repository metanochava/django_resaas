"""
`@resaas_action` is a supported extension point (see
docs/development/creating-resource.md) but isn't actually applied to any
real view in this codebase yet - these tests exercise it directly against a
throwaway ViewSet so the mechanism itself stays covered.
"""
import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
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


def test_sync_view_alone_never_removes_orphans():
    """
    sync_view() only upserts what IS declared on the view passed in - it
    must never delete anything, since it has no way of knowing whether
    some other view of the same model still declares an action it
    doesn't see here (see test_sync_registry_still_removes_a_true_orphan_
    across_views below for where orphan removal actually happens).
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


# =========================================================
# INHERITANCE
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


def test_action_inherited_from_a_mixin_is_discovered():
    ActionSyncService.sync_view(_ViewInheritingAction)

    extra = ModelExtraAction.objects.get(app="demo", model="product", action="pay")
    assert extra.label == "Pay"


def test_subclass_override_of_an_inherited_action_wins():
    ActionSyncService.sync_view(_ViewOverridingInheritedAction)

    extra = ModelExtraAction.objects.get(app="demo", model="product", action="pay")
    assert extra.label == "Pay (overridden)"


class _ViewOverridingInheritedActionWithoutDecorator(_PaymentMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # deliberately overrides the mixin's @resaas_action "pay" with a plain
    # method - this subclass no longer wants it to be a RESAAS action
    def pay(self, request, pk=None):
        ...


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
# MULTIPLE VIEWS OF THE SAME MODEL (sync_registry)
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


def test_sync_registry_does_not_delete_actions_from_a_sibling_view_of_the_same_model():
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
# EXPLICIT permission=
# =========================================================

class _ViewWithExplicitPermission(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @resaas_action(
        detail=True, methods=["post"], label="Confirm",
        permission="confirm_sale",
    )
    def confirm(self, request, pk=None):
        ...


def test_explicit_permission_is_used_instead_of_the_default_codename():
    ActionSyncService.sync_view(_ViewWithExplicitPermission)

    extra = ModelExtraAction.objects.get(
        app="demo", model="product", action="confirm"
    )
    assert extra.permission == "confirm_sale"
    assert Permission.objects.filter(codename="confirm_sale").exists()
    # the default-convention codename was NOT also created
    assert not Permission.objects.filter(codename="confirm_product").exists()


def test_action_without_explicit_permission_still_falls_back_to_the_default():
    ActionSyncService.sync_view(_ViewWithArchiveAction)

    extra = ModelExtraAction.objects.get(
        app="demo", model="product", action="archive"
    )
    assert extra.permission == "archive_product"


def test_explicit_permission_lookup_is_scoped_to_the_right_content_type():
    """
    A permission with the same codename can legitimately exist on a
    DIFFERENT model - _sync_action must not reuse that unrelated
    Permission row just because the codename string matches; it has to
    be looked up (and created, if missing) for THIS model's ContentType.
    """
    from django.contrib.auth.models import Group as DjangoGroup
    from django.contrib.contenttypes.models import ContentType as CT

    other_permission = Permission.objects.create(
        content_type=CT.objects.get_for_model(DjangoGroup),
        codename="confirm_sale",
        name="Some unrelated permission on a different model",
    )

    ActionSyncService.sync_view(_ViewWithExplicitPermission)

    extra = ModelExtraAction.objects.get(
        app="demo", model="product", action="confirm"
    )
    product_permission = Permission.objects.get(
        content_type=ContentType.objects.get_for_model(Product),
        codename="confirm_sale",
    )

    assert extra.permission == "confirm_sale"
    assert product_permission.id != other_permission.id


def test_explicit_permission_does_not_get_its_name_rewritten():
    """A shared/explicit permission's name isn't "owned" by any single
    action, so _sync_action must never rename it, even when it's
    RESAAS-managed."""
    ActionSyncService.sync_view(_ViewWithExplicitPermission)

    permission = Permission.objects.get(codename="confirm_sale")
    permission.name = "Confirm Sale (custom wording)"
    permission.save(update_fields=["name"])

    ActionSyncService.sync_view(_ViewWithExplicitPermission)

    permission.refresh_from_db()
    assert permission.name == "Confirm Sale (custom wording)"


# =========================================================
# MANUAL VS DECORATOR COLLISION
# =========================================================

def test_decorator_never_silently_takes_over_a_manual_action():
    from django.core.exceptions import ImproperlyConfigured

    ModelExtraAction.objects.create(
        app="demo",
        model="product",
        action="archive",
        label="Archive (hand-configured)",
        managed_by="manual",
    )

    with pytest.raises(ImproperlyConfigured):
        ActionSyncService.sync_view(_ViewWithArchiveAction)

    # untouched by the failed sync
    extra = ModelExtraAction.objects.get(
        app="demo", model="product", action="archive"
    )
    assert extra.managed_by == "manual"
    assert extra.label == "Archive (hand-configured)"


def test_decorator_can_sync_freely_once_ownership_is_explicitly_transferred():
    ModelExtraAction.objects.create(
        app="demo",
        model="product",
        action="archive",
        label="Archive (hand-configured)",
        managed_by="decorator",  # explicit takeover, done by a human
    )

    # no exception - "decorator" is fair game for the decorator to sync
    ActionSyncService.sync_view(_ViewWithArchiveAction)

    extra = ModelExtraAction.objects.get(
        app="demo", model="product", action="archive"
    )
    assert extra.label == "Archive"


# =========================================================
# PERMISSION OWNERSHIP
# =========================================================

def test_manually_created_permission_is_never_deleted_as_an_orphan():
    # a permission that pre-exists the decorator (e.g. created by a human
    # via the admin) must be marked as NOT managed by RESAAS ...
    Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Product),
        codename="archive_product",
        name="Manually created permission",
    )

    ActionSyncService.sync_view(_ViewWithArchiveAction)
    extra = ModelExtraAction.objects.get(
        app="demo", model="product", action="archive"
    )
    assert extra.permission_managed is False

    # ... so removing the action later must not delete the permission
    ActionSyncService.sync_registry({"demo": {"archive": _ViewWithNoActions}})

    assert not ModelExtraAction.objects.filter(
        app="demo", model="product", action="archive"
    ).exists()
    assert Permission.objects.filter(codename="archive_product").exists()


def test_managed_permission_name_is_refreshed_when_stale():
    ActionSyncService.sync_view(_ViewWithArchiveAction)

    permission = Permission.objects.get(codename="archive_product")
    permission.name = "Stale name"
    permission.save(update_fields=["name"])

    ActionSyncService.sync_view(_ViewWithArchiveAction)

    permission.refresh_from_db()
    assert permission.name == "Can archive product"


def test_manually_managed_permission_name_is_left_alone():
    Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Product),
        codename="archive_product",
        name="Do not touch this",
    )
    ActionSyncService.sync_view(_ViewWithArchiveAction)

    ActionSyncService.sync_view(_ViewWithArchiveAction)

    permission = Permission.objects.get(codename="archive_product")
    assert permission.name == "Do not touch this"
