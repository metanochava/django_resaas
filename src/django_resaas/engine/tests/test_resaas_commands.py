"""
Tests for the resaas_setup / resaas_sync / resaas_doctor / resaas_check /
resaas_schema_check command layer, the dry_run mode ActionSyncService
gained to back it, and backward compatibility of the legacy `sync_actions`/
`setup` wrapper commands.

Uses the same throwaway-ViewSet-against-`dev.demo.Product` pattern as
test_action_sync.py, plus a `clean_registry` fixture that swaps out the
real (shared, mutable) VIEW_REGISTRY dict's contents for the duration of a
test - the commands under test import VIEW_REGISTRY by reference, so
mutating it in place is visible to them without needing to patch imports
in three different command modules.
"""
import json
from io import StringIO

import pytest
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.viewsets import ModelViewSet

from dev.demo.models import Product
from dev.demo.serializers import ProductSerializer
from django_resaas.engine.core.base.registry import VIEW_REGISTRY
from django_resaas.engine.core.decorators.action import resaas_action
from django_resaas.engine.core.services.action_sync_service import ActionSyncService
from django_resaas.engine.models.model_extra_action import ModelExtraAction

pytestmark = pytest.mark.django_db


class _ViewWithShipAction(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @resaas_action(detail=True, methods=["post"], label="Ship")
    def ship(self, request, pk=None):
        ...


class _ViewWithNoActions(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class _ViewWithNoModel:
    """Deliberately not a real DRF view - no queryset, no serializer_class -
    so ActionSyncService._get_model_from_view() returns None. Used to
    trigger RegistryCheck's warning path deterministically."""


@pytest.fixture
def clean_registry():
    saved = {key: dict(value) for key, value in VIEW_REGISTRY.items()}
    VIEW_REGISTRY.clear()
    try:
        yield VIEW_REGISTRY
    finally:
        VIEW_REGISTRY.clear()
        VIEW_REGISTRY.update(saved)


def _run(command, *args, **kwargs):
    out, err = StringIO(), StringIO()
    kwargs.setdefault("stdout", out)
    kwargs.setdefault("stderr", err)
    call_command(command, *args, **kwargs)
    return out.getvalue(), err.getvalue()


# =========================================================
# ActionSyncService.dry_run
# =========================================================

def test_action_sync_service_dry_run_creates_nothing():
    summary = ActionSyncService.sync_view(_ViewWithShipAction, dry_run=True)

    assert summary.created == ["demo.product.ship"]
    assert not ModelExtraAction.objects.filter(
        app="demo", model="product", action="ship"
    ).exists()
    assert not Permission.objects.filter(codename="ship_product").exists()


def test_action_sync_service_dry_run_then_real_run_applies():
    ActionSyncService.sync_view(_ViewWithShipAction, dry_run=True)
    assert not ModelExtraAction.objects.filter(
        app="demo", model="product", action="ship"
    ).exists()

    summary = ActionSyncService.sync_view(_ViewWithShipAction, dry_run=False)

    assert summary.created == ["demo.product.ship"]
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="ship"
    ).exists()


def test_action_sync_service_dry_run_reports_unchanged_not_updated():
    ActionSyncService.sync_view(_ViewWithShipAction)  # real run, seeds the row

    summary = ActionSyncService.sync_view(_ViewWithShipAction, dry_run=True)

    assert summary.unchanged == ["demo.product.ship"]
    assert summary.created == []
    assert summary.updated == []


def test_action_sync_registry_dry_run_reports_orphan_without_deleting():
    registry_with_action = {"demo": {"ship": _ViewWithShipAction}}
    ActionSyncService.sync_registry(registry_with_action)
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="ship"
    ).exists()

    registry_without_action = {"demo": {"ship": _ViewWithNoActions}}
    summary = ActionSyncService.sync_registry(registry_without_action, dry_run=True)

    assert summary.deleted == ["demo.product.ship"]
    # still there - dry run must not have actually deleted it
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="ship"
    ).exists()
    assert Permission.objects.filter(codename="ship_product").exists()


# =========================================================
# resaas_sync
# =========================================================

def test_resaas_sync_creates_then_second_run_is_idempotent(clean_registry):
    clean_registry["demo"] = {"ship": _ViewWithShipAction}

    out1, _ = _run("resaas_sync", verbosity=2)
    assert "Created: 1" in out1
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="ship"
    ).exists()

    out2, _ = _run("resaas_sync", verbosity=2)
    assert "Created: 0" in out2
    assert "Unchanged:   1" in out2
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="ship"
    ).count() == 1


def test_resaas_sync_dry_run_does_not_touch_db(clean_registry):
    clean_registry["demo"] = {"ship": _ViewWithShipAction}

    out, _ = _run("resaas_sync", dry_run=True)

    assert "Would create: 1" in out
    assert not ModelExtraAction.objects.filter(
        app="demo", model="product", action="ship"
    ).exists()


def test_resaas_sync_empty_registry_warns_and_does_not_crash(clean_registry):
    out, _ = _run("resaas_sync")
    assert "VIEW_REGISTRY is empty" in out


# =========================================================
# resaas_doctor
# =========================================================

def test_resaas_doctor_healthy_project_exits_zero(clean_registry):
    clean_registry["demo"] = {"ship": _ViewWithShipAction}
    ActionSyncService.sync_registry(clean_registry)  # pre-sync so ActionCheck is clean

    out, _ = _run("resaas_doctor")

    assert "Status      OK" in out
    assert "ERROR" not in out


def test_resaas_doctor_reports_info_for_model_less_registered_view(clean_registry):
    # A registered view with no resolvable model (dashboards, scaffold,
    # notification catalog, ...) is a normal, valid shape in this codebase
    # - not eligible for action sync/schema, but not a defect either. Must
    # surface as "info", never as a WARNING/ERROR that would falsely fail
    # a healthy install (see resaas_doctor run against the real dev
    # backend, which has exactly this kind of view).
    clean_registry["demo"] = {"broken": _ViewWithNoModel}

    out, _ = _run("resaas_doctor")

    assert "WARNING" not in out
    assert "ERROR" not in out
    assert "Status      OK" in out


def test_resaas_doctor_reports_warning_for_unsynced_action(clean_registry):
    # A real @resaas_action that was never synced - a genuine, actionable
    # warning (unlike the model-less-view case above).
    clean_registry["demo"] = {"ship": _ViewWithShipAction}

    out, _ = _run("resaas_doctor")

    assert "WARNING" in out
    assert "exists in code but not in persisted metadata" in out


def test_resaas_doctor_json_output_is_valid_json_only(clean_registry):
    clean_registry["demo"] = {"ship": _ViewWithShipAction}
    ActionSyncService.sync_registry(clean_registry)

    out, _ = _run("resaas_doctor", as_json=True)
    payload = json.loads(out)  # raises if anything but JSON was written

    assert payload["status"] == "ok"
    assert payload["errors"] == 0
    assert isinstance(payload["checks"], list)
    assert any(c["check"] == "database" for c in payload["checks"])


def test_resaas_doctor_fail_on_warning_exits_1(clean_registry):
    clean_registry["demo"] = {"ship": _ViewWithShipAction}  # unsynced -> warning

    with pytest.raises(SystemExit) as excinfo:
        call_command("resaas_doctor", stdout=StringIO(), fail_on_warning=True)

    assert excinfo.value.code == 1


def test_resaas_doctor_warning_without_fail_on_warning_does_not_exit_nonzero(clean_registry):
    clean_registry["demo"] = {"ship": _ViewWithShipAction}  # unsynced -> warning

    # no SystemExit at all - only --fail-on-warning turns a warning-only
    # report into a non-zero exit code
    out, _ = _run("resaas_doctor")
    assert "WARNING" in out


def test_resaas_doctor_check_filter_runs_only_named_check():
    out, _ = _run("resaas_doctor", only_checks=["database"])

    assert "Database" in out
    assert "Migrations" not in out


def test_resaas_doctor_unknown_check_raises_command_error():
    with pytest.raises(CommandError):
        call_command("resaas_doctor", stdout=StringIO(), only_checks=["nope"])


def test_resaas_check_is_an_alias_of_resaas_doctor(clean_registry):
    clean_registry["demo"] = {"ship": _ViewWithShipAction}
    ActionSyncService.sync_registry(clean_registry)

    out, _ = _run("resaas_check")
    assert "RESAAS Doctor" in out
    assert "Status      OK" in out


# =========================================================
# resaas_schema_check
# =========================================================

def test_resaas_schema_check_healthy_model_reports_ok(clean_registry):
    clean_registry["demo"] = {"ship": _ViewWithShipAction}

    out, _ = _run("resaas_schema_check")
    assert "OK" in out


def test_resaas_schema_check_reports_build_failure(monkeypatch, clean_registry):
    clean_registry["demo"] = {"ship": _ViewWithShipAction}

    from django_resaas.engine.core.schema.builder import ResaasSchemaBuilder

    def _boom(self):
        raise RuntimeError("boom")

    monkeypatch.setattr(ResaasSchemaBuilder, "build", _boom)

    with pytest.raises(SystemExit) as excinfo:
        call_command("resaas_schema_check", stdout=StringIO())

    assert excinfo.value.code == 2


# =========================================================
# Legacy wrapper compatibility
# =========================================================

def test_sync_actions_wrapper_still_works(clean_registry):
    clean_registry["demo"] = {"ship": _ViewWithShipAction}

    out, _ = _run("sync_actions")

    assert "RESAAS Actions synced" in out
    assert ModelExtraAction.objects.filter(
        app="demo", model="product", action="ship"
    ).exists()


def test_setup_wrapper_still_works():
    out, _ = _run("setup")
    assert "Sistema pronto para uso" in out


def test_resaas_setup_runs_the_same_underlying_logic():
    out, _ = _run("resaas_setup")
    assert "RESAAS ready." in out
