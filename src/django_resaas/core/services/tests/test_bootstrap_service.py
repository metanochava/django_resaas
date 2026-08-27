"""
Regression test for a real bug found while building the demo app (Phase 6):
BootstrapService/create_root/app_service all created App/EntityApp rows with
`state=1` (an int, coerced to the string "1" on a CharField), but the actual
per-request gate in BaseAPIView.initial() checks `state="Active"`. That meant
every tenant bootstrapped via these paths got a 403 ("Module is not active")
on every single API call - confirmed empirically before the fix.

Fixed in BootstrapService.create_entity, create_root.py, and
management/apicommands/service/app_service.py by writing state="Active"
directly for App/EntityApp (the two models the live gate actually checks),
with a self-heal step so it also repairs any pre-existing state="1" row
instead of crashing on the (entity, app) unique constraint.
"""
import pytest
from django.contrib.auth import get_user_model

from django_resaas.core.services.bootstrap_service import BootstrapService
from django_resaas.models.app import App
from django_resaas.models.entity_app import EntityApp

pytestmark = pytest.mark.django_db


def _make_user():
    return get_user_model().objects.create_user(
        username="bootstrap-user",
        email="bootstrap-user@example.com",
        password="pass-123",
    )


def test_bootstrapped_hr_app_is_actually_active():
    user = _make_user()

    result = BootstrapService.run(
        "SaaS", "Tenant", "Main", user, "Admin",
    )

    entity_app = EntityApp.objects.get(
        entity=result["entity"],
        app__name="hr",
    )
    assert entity_app.state == "Active"

    # this is exactly what BaseAPIView.initial() checks before letting any
    # request through - it must find this row.
    assert EntityApp.objects.filter(
        entity__id=result["entity"].id,
        app__name="hr",
        state="Active",
    ).exists()


def test_bootstrap_self_heals_a_preexisting_broken_row():
    """A row already broken by the old `state=1` behavior gets repaired on
    the next bootstrap run instead of causing a duplicate-row crash."""
    user = _make_user()

    result = BootstrapService.run("SaaS", "Tenant", "Main", user, "Admin")
    entity_app = EntityApp.objects.get(entity=result["entity"], app__name="hr")

    # simulate a row left over from the old buggy code path
    entity_app.state = "1"
    entity_app.save(update_fields=["state"])

    # running bootstrap again must not raise (no duplicate (entity, app) row)
    # and must heal the existing row back to "Active"
    BootstrapService.run("SaaS", "Tenant", "Main", user, "Admin")

    entity_app.refresh_from_db()
    assert entity_app.state == "Active"
    assert EntityApp.objects.filter(
        entity=result["entity"], app__name="hr"
    ).count() == 1
