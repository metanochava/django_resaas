"""
FASE 1 - P0.4: permission ownership and lifecycle around @resaas_action.

Covers: automatic vs explicit permission codenames, ContentType-scoped
lookup, manual actions/permissions never taken over or deleted
automatically, and managed permissions having a controlled lifecycle
(name kept in sync, removed when their action is removed).
"""
import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from rest_framework.viewsets import ModelViewSet

from dev.demo.models import Product
from dev.demo.serializers import ProductSerializer
from django_resaas.engine.core.decorators.action import resaas_action
from django_resaas.engine.core.services.action_sync_service import ActionSyncService
from django_resaas.engine.models.model_extra_action import ModelExtraAction

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


class _ViewWithExplicitPermission(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @resaas_action(
        detail=True, methods=["post"], label="Confirm",
        permission="confirm_sale",
    )
    def confirm(self, request, pk=None):
        ...


# =========================================================
# PERMISSION AUTOMÁTICA VS EXPLÍCITA
# =========================================================

def test_action_without_explicit_permission_falls_back_to_the_default_codename():
    ActionSyncService.sync_view(_ViewWithArchiveAction)

    extra = ModelExtraAction.objects.get(
        app="demo", model="product", action="archive"
    )
    assert extra.permission == "archive_product"


def test_explicit_permission_is_used_instead_of_the_default_codename():
    ActionSyncService.sync_view(_ViewWithExplicitPermission)

    extra = ModelExtraAction.objects.get(
        app="demo", model="product", action="confirm"
    )
    assert extra.permission == "confirm_sale"
    assert Permission.objects.filter(codename="confirm_sale").exists()
    # the default-convention codename was NOT also created
    assert not Permission.objects.filter(codename="confirm_product").exists()


# =========================================================
# CONTENTTYPE + CODENAME
# =========================================================

def test_permission_lookup_is_scoped_to_the_right_content_type():
    """
    A permission with the same codename can legitimately exist on a
    DIFFERENT model - _sync_action must not reuse that unrelated
    Permission row just because the codename string matches; it has to
    be looked up (and created, if missing) for THIS model's ContentType.
    """
    from django.contrib.auth.models import Group as DjangoGroup

    other_permission = Permission.objects.create(
        content_type=ContentType.objects.get_for_model(DjangoGroup),
        codename="confirm_sale",
        name="Some unrelated permission on a different model",
    )

    ActionSyncService.sync_view(_ViewWithExplicitPermission)

    product_permission = Permission.objects.get(
        content_type=ContentType.objects.get_for_model(Product),
        codename="confirm_sale",
    )

    assert product_permission.id != other_permission.id


# =========================================================
# MANUAL ACTION NÃO PODE SER ROUBADA
# =========================================================

def test_manual_action_cannot_be_taken_over_by_decorator():
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


def test_decorator_can_sync_once_ownership_is_explicitly_transferred():
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
# PERMISSION MANUAL NÃO PODE SER APAGADA
# =========================================================

def test_manual_permission_survives_orphan_cleanup():
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

    # ... so removing the action later (via sync_registry, the only entry
    # point that actually removes orphans) must not delete the permission
    ActionSyncService.sync_registry({"demo": {"archive": _ViewWithNoActions}})

    assert not ModelExtraAction.objects.filter(
        app="demo", model="product", action="archive"
    ).exists()
    assert Permission.objects.filter(codename="archive_product").exists()


# =========================================================
# PERMISSION GERIDA: LIFECYCLE CONTROLADO
# =========================================================

def test_managed_permission_name_is_kept_in_sync():
    ActionSyncService.sync_view(_ViewWithArchiveAction)

    permission = Permission.objects.get(codename="archive_product")
    permission.name = "Stale name"
    permission.save(update_fields=["name"])

    ActionSyncService.sync_view(_ViewWithArchiveAction)

    permission.refresh_from_db()
    assert permission.name == "Can archive product"


def test_managed_permission_is_removed_when_its_action_is_removed():
    registry_with_action = {"demo": {"archive": _ViewWithArchiveAction}}
    ActionSyncService.sync_registry(registry_with_action)

    extra = ModelExtraAction.objects.get(
        app="demo", model="product", action="archive"
    )
    assert extra.permission_managed is True
    assert Permission.objects.filter(codename="archive_product").exists()

    # the action disappears from code entirely
    registry_without_action = {"demo": {"archive": _ViewWithNoActions}}
    ActionSyncService.sync_registry(registry_without_action)

    assert not ModelExtraAction.objects.filter(
        app="demo", model="product", action="archive"
    ).exists()
    assert not Permission.objects.filter(codename="archive_product").exists()


def test_manually_managed_permission_name_is_never_rewritten():
    Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Product),
        codename="archive_product",
        name="Do not touch this",
    )
    ActionSyncService.sync_view(_ViewWithArchiveAction)
    ActionSyncService.sync_view(_ViewWithArchiveAction)

    permission = Permission.objects.get(codename="archive_product")
    assert permission.name == "Do not touch this"


# =========================================================
# PERMISSION EXPLÍCITA REUTILIZADA
# =========================================================

def test_explicit_permission_is_never_renamed():
    """A shared/explicit permission's name isn't "owned" by any single
    action, so _sync_action must never rename it - even though it IS
    RESAAS-managed (it was created by this same sync)."""
    ActionSyncService.sync_view(_ViewWithExplicitPermission)

    permission = Permission.objects.get(codename="confirm_sale")
    permission.name = "Confirm Sale (custom wording)"
    permission.save(update_fields=["name"])

    ActionSyncService.sync_view(_ViewWithExplicitPermission)

    permission.refresh_from_db()
    assert permission.name == "Confirm Sale (custom wording)"


def test_explicit_permission_is_not_deleted_when_its_action_is_removed():
    """
    An explicit permission= is, by definition, meant to be shared/reused -
    a single action going away must not assume ownership and delete it,
    even though the ModelExtraAction row for THIS action is itself
    permission_managed=True (it was the one that happened to create it).
    """
    registry_with_action = {"demo": {"confirm": _ViewWithExplicitPermission}}
    ActionSyncService.sync_registry(registry_with_action)
    assert Permission.objects.filter(codename="confirm_sale").exists()

    # the "confirm" action disappears from code entirely
    registry_without_action = {"demo": {"confirm": _ViewWithNoActions}}
    ActionSyncService.sync_registry(registry_without_action)

    assert not ModelExtraAction.objects.filter(
        app="demo", model="product", action="confirm"
    ).exists()
    assert Permission.objects.filter(codename="confirm_sale").exists()
