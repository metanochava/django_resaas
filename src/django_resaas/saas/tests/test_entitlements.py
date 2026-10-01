"""Entitlements (core/entitlements/): features, capacities and modules an
installation/tenant may use - separate from permissions, enforced by the
backend whatever the frontend shows. See docs/security/entitlements.md."""
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from django_resaas.saas.core.entitlements import (
    CapacityExceeded,
    EntitlementContext,
    EntitlementProvider,
    FeatureNotAvailable,
    get_capacity,
    get_provider,
    has_feature,
    has_module,
    require_capacity,
    require_feature,
)
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.tests.test_permission_api_security import _actor

pytestmark = pytest.mark.django_db

CTX = EntitlementContext(entity_id=None)
BRANCHES = "/api/django_resaas/branchs/"

LIMITED = {
    "features": {"multi_entity": False, "advanced_audit": True},
    "capacities": {"branches": 2, "users": 3, "entities": 5, "entity_types": 5},
}


class BrokenProvider(EntitlementProvider):
    def is_restricted(self, context):
        raise RuntimeError("license server down")

    def has_feature(self, context, feature):
        raise RuntimeError("license server down")

    def get_capacity(self, context, capacity):
        raise RuntimeError("license server down")

    def has_module(self, context, module):
        raise RuntimeError("license server down")


class PerEntityProvider(EntitlementProvider):
    """A provider that answers per tenant - what a SaaS/database provider does."""

    def get_capacity(self, context, capacity):
        return 1 if capacity == "branches" and context.entity_id else None


# ------------------------------------------------------------------ service

def test_not_configured_restricts_nothing():
    assert has_feature(CTX, "anything") is True
    assert get_capacity(CTX, "branches") is None
    require_capacity(CTX, "branches", current=10_000)
    assert has_module(CTX, "some_module") is True


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_feature_enabled_disabled_and_unknown():
    assert has_feature(CTX, "advanced_audit") is True
    assert has_feature(CTX, "multi_entity") is False
    assert has_feature(CTX, "never_heard_of") is False  # configured: fail closed

    require_feature(CTX, "advanced_audit")
    with pytest.raises(FeatureNotAvailable) as error:
        require_feature(CTX, "multi_entity")
    assert error.value.status_code == 403
    assert error.value.resaas_code == "feature_not_available"


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
@pytest.mark.parametrize("current,allowed", [(0, True), (1, True), (2, False), (5, False)])
def test_capacity_below_at_and_over_the_limit(current, allowed):
    if allowed:
        require_capacity(CTX, "branches", current=current)
        return

    with pytest.raises(CapacityExceeded) as error:
        require_capacity(CTX, "branches", current=current)
    assert error.value.status_code == 403
    assert error.value.resaas_code == "capacity_exceeded"
    assert error.value.resaas_details == {"capacity": "branches", "limit": 2, "current": current}


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_unknown_capacity_is_zero_when_configured():
    assert get_capacity(CTX, "invoices_per_month") == 0
    with pytest.raises(CapacityExceeded):
        require_capacity(CTX, "invoices_per_month", current=0)


def test_a_capacity_without_counter_needs_current():
    with override_settings(RESAAS_ENTITLEMENTS={"capacities": {"invoices_per_month": 10}}):
        with pytest.raises(ValueError):
            require_capacity(CTX, "invoices_per_month")
        require_capacity(CTX, "invoices_per_month", current=9)


@override_settings(RESAAS_ENTITLEMENT_PROVIDER=f"{__name__}.BrokenProvider")
def test_provider_failure_denies():
    assert isinstance(get_provider(), BrokenProvider)
    assert has_feature(CTX, "advanced_audit") is False
    assert get_capacity(CTX, "branches") == 0
    assert has_module(CTX, "demo") is False
    with pytest.raises(CapacityExceeded):
        require_capacity(CTX, "branches", current=0)


def test_framework_modules_always_run_and_modules_list_is_optional():
    with override_settings(RESAAS_ENTITLEMENTS={"modules": ["demo"]}):
        assert has_module(CTX, "django_resaas") is True
        assert has_module(CTX, "notifications") is True
        assert has_module(CTX, "demo") is True
        assert has_module(CTX, "sales") is False

    with override_settings(RESAAS_ENTITLEMENTS={"features": {}}):
        assert has_module(CTX, "sales") is True


# ------------------------------------------------------------------ API: capacities

def _new_branch(client, name):
    return client.post(BRANCHES, {"name": name}, format="json")


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_branch_creation_stops_exactly_at_the_limit(bootstrap_tenant):
    tenant = bootstrap_tenant("ent-branch")  # already has 1 branch (Main)

    assert _new_branch(tenant["client"], "Second").status_code == 201

    response = _new_branch(tenant["client"], "Third")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "capacity_exceeded"
    assert response.json()["error"]["details"] == {"capacity": "branches", "limit": 2, "current": 2}
    assert not Branch.objects.filter(entity=tenant["entity"], name="Third").exists()


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_details_stay_machine_values_in_any_language(bootstrap_tenant):
    """The message is translated; details.capacity ("branches") and the numbers
    are a contract - never "Sucursais" / "2"."""
    from django.core.cache import cache

    from django_resaas.saas.models.language import Language

    Language.objects.get_or_create(code="pt-pt", defaults={"name": "Português"})
    portuguese = Language.objects.get(code="pt-pt")
    cache.clear()
    tenant = bootstrap_tenant("ent-lang")
    _new_branch(tenant["client"], "Second")

    response = tenant["client"].post(BRANCHES, {"name": "Third"}, format="json", HTTP_L=str(portuguese.id))

    error = response.json()["error"]
    assert error["details"] == {"capacity": "branches", "limit": 2, "current": 2}
    assert error["code"] == "capacity_exceeded"


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_capacity_is_counted_per_tenant(bootstrap_tenant):
    full = bootstrap_tenant("ent-iso-a")
    other = bootstrap_tenant("ent-iso-b")
    assert _new_branch(full["client"], "A2").status_code == 201
    assert _new_branch(full["client"], "A3").status_code == 403

    # another Entity's usage does not consume this one's capacity
    assert _new_branch(other["client"], "B2").status_code == 201


@override_settings(RESAAS_ENTITLEMENT_PROVIDER=f"{__name__}.PerEntityProvider")
def test_provider_receives_the_signed_tenant_context(bootstrap_tenant):
    tenant = bootstrap_tenant("ent-ctx")  # 1 branch, provider allows 1

    response = _new_branch(tenant["client"], "Second")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "capacity_exceeded"


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_superuser_is_subject_to_capacities(bootstrap_tenant):
    """A capacity is not a permission: being superuser/Root does not lift it."""
    tenant = bootstrap_tenant("ent-super")
    tenant["user"].is_superuser = True
    tenant["user"].save(update_fields=["is_superuser"])
    assert _new_branch(tenant["client"], "Second").status_code == 201

    assert _new_branch(tenant["client"], "Third").status_code == 403


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_entity_admin_is_subject_to_capacities(bootstrap_tenant):
    tenant = bootstrap_tenant("ent-admin")
    tenant["entity"].admins.add(tenant["user"])
    assert _new_branch(tenant["client"], "Second").status_code == 201

    assert _new_branch(tenant["client"], "Third").status_code == 403


@override_settings(RESAAS_ENTITLEMENTS={"capacities": {"users": 10}})
def test_capacity_never_replaces_the_permission(bootstrap_tenant):
    """Both must pass: seats available but no add_entityuser -> 403, nothing created."""
    tenant = bootstrap_tenant("ent-perm")
    client = _actor(tenant, "ent-perm-actor", "view_entity")
    newcomer = get_user_model().objects.create_user(
        username="ent-perm-new", email="ent-perm-new@example.com", password="pass-12345"
    )

    response = client.post(
        f"/api/django_resaas/entitys/{tenant['entity'].id}/addUser/", {"user": newcomer.id}, format="json"
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
    assert not EntityUser.objects.filter(user=newcomer).exists()


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_hiding_the_button_is_not_the_protection(bootstrap_tenant):
    """A client that ignores the UX (calls the API directly) is still refused."""
    tenant = bootstrap_tenant("ent-bypass")
    _new_branch(tenant["client"], "Second")

    raw = APIClient()
    raw.force_authenticate(user=tenant["user"])
    raw.credentials(HTTP_X_RESAAS_CONTEXT=tenant["context"]["token"], HTTP_L="1")

    assert _new_branch(raw, "Forced").status_code == 403


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_adding_users_to_an_entity_stops_at_the_limit(bootstrap_tenant):
    tenant = bootstrap_tenant("ent-users")
    url = f"/api/django_resaas/entitys/{tenant['entity'].id}/addUser/"
    users = [
        get_user_model().objects.create_user(username=f"ent-users-{i}", email=f"ent-users-{i}@example.com", password="pass-12345")
        for i in range(3)
    ]
    used = EntityUser.objects.filter(entity=tenant["entity"], state="Active").count()

    responses = [tenant["client"].post(url, {"user": user.id}, format="json") for user in users]

    allowed = LIMITED["capacities"]["users"] - used
    assert [r.status_code for r in responses[:allowed]] == [201] * allowed
    assert responses[allowed].status_code == 403
    assert responses[allowed].json()["error"]["code"] == "capacity_exceeded"
    assert EntityUser.objects.filter(entity=tenant["entity"], state="Active").count() == 3


# ------------------------------------------------------------------ API: modules

MEMBERS = "/api/demo/members/"


def test_module_outside_the_entitlements_is_refused_even_when_active(bootstrap_tenant):
    tenant = bootstrap_tenant("ent-mod-off", modules=("demo",))

    with override_settings(RESAAS_ENTITLEMENTS={"modules": ["demo"]}):
        assert tenant["client"].get(MEMBERS).status_code == 200

    with override_settings(RESAAS_ENTITLEMENTS={"modules": []}):
        response = tenant["client"].get(MEMBERS)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "module_not_available"


@override_settings(RESAAS_ENTITLEMENTS={"modules": ["demo"]})
def test_entitlement_never_activates_a_module(bootstrap_tenant):
    tenant = bootstrap_tenant("ent-mod-inactive")  # demo not activated (EntityApp)

    response = tenant["client"].get(MEMBERS)

    assert response.status_code == 403
    assert response.json()["error"]["code"] != "module_not_available"


# ------------------------------------------------------------------ API: snapshot endpoint

URL = "/api/resaas/entitlements/"


def test_snapshot_needs_authentication():
    assert APIClient().get(URL).status_code in (401, 403)


def test_snapshot_needs_the_tenant_context(bootstrap_tenant):
    tenant = bootstrap_tenant("ent-snap-noctx")
    client = APIClient()
    client.force_authenticate(user=tenant["user"])

    assert client.get(URL).status_code == 403


def test_snapshot_when_nothing_is_restricted(bootstrap_tenant):
    tenant = bootstrap_tenant("ent-snap-open")

    data = tenant["client"].get(URL).json()

    assert data["restricted"] is False
    assert data["features"] == {}
    assert data["capacities"]["branches"] == {"limit": None, "used": 1}
    assert set(data["capacities"]) == {"branches", "entities", "entity_types", "users"}


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_snapshot_reports_limits_and_the_current_tenants_usage(bootstrap_tenant):
    tenant = bootstrap_tenant("ent-snap")
    bootstrap_tenant("ent-snap-other")

    data = tenant["client"].get(URL).json()

    assert data["restricted"] is True
    assert data["features"] == {"multi_entity": False, "advanced_audit": True}
    assert data["capacities"]["branches"] == {"limit": 2, "used": 1}
    assert data["capacities"]["users"]["limit"] == 3


# ------------------------------------------------------------------ tenant comes from the signed context

def test_snapshot_refuses_a_tampered_context(bootstrap_tenant):
    tenant = bootstrap_tenant("ent-snap-tampered")
    client = APIClient()
    client.force_authenticate(user=tenant["user"])
    client.credentials(HTTP_X_RESAAS_CONTEXT=tenant["context"]["token"] + "x", HTTP_L="1")

    assert client.get(URL).status_code == 403


@override_settings(RESAAS_ENTITLEMENTS=LIMITED)
def test_tenant_ids_in_the_body_do_not_move_the_capacity_check(bootstrap_tenant):
    """The capacity is counted on the Entity of the signed context: naming
    another Entity (with room left) in the body changes nothing."""
    full = bootstrap_tenant("ent-body-a")
    other = bootstrap_tenant("ent-body-b")
    _new_branch(full["client"], "A2")  # full: 2 of 2

    response = full["client"].post(
        BRANCHES,
        {"name": "Sneaky", "entity": str(other["entity"].id), "entity_id": str(other["entity"].id)},
        format="json",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "capacity_exceeded"
    assert not Branch.objects.filter(name="Sneaky").exists()


# ------------------------------------------------------------------ installation-wide capacities through the API

def test_entity_types_capacity_through_the_api(bootstrap_tenant):
    from django_resaas.saas.models.entity_type import EntityType

    tenant = bootstrap_tenant("ent-types")
    used = EntityType.objects.count()

    with override_settings(RESAAS_ENTITLEMENTS={"capacities": {"entity_types": used + 1}}):
        first = tenant["client"].post("/api/django_resaas/entitytypes/", {"name": "Clinic"}, format="json")
        second = tenant["client"].post("/api/django_resaas/entitytypes/", {"name": "School"}, format="json")

    assert first.status_code == 201
    assert second.status_code == 403
    assert second.json()["error"]["details"] == {"capacity": "entity_types", "limit": used + 1, "current": used + 1}
    assert not EntityType.objects.filter(name="School").exists()


def test_entities_capacity_through_the_api(bootstrap_tenant):
    from django_resaas.saas.models.entity import Entity

    tenant = bootstrap_tenant("ent-entities")
    used = Entity.objects.count()
    payload = {"name": "Second Org", "entity_type": str(tenant["entity"].entity_type_id),
               "admins": [str(tenant["user"].id)]}

    with override_settings(RESAAS_ENTITLEMENTS={"capacities": {"entities": used, "branches": None, "users": None}}):
        response = tenant["client"].post("/api/django_resaas/entitys/", payload, format="json")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "capacity_exceeded"
    assert Entity.objects.count() == used  # nothing half-created (atomic)


# ------------------------------------------------------------------ frontend contract

def test_snapshot_shape_is_what_the_entitlement_store_reads(bootstrap_tenant):
    """quasar_resaas EntitlementStore reads exactly: restricted (bool),
    features ({name: bool}) and capacities ({name: {limit: int|null, used: int}})."""
    tenant = bootstrap_tenant("ent-contract")

    with override_settings(RESAAS_ENTITLEMENTS=LIMITED):
        data = tenant["client"].get(URL).json()

    assert set(data) == {"restricted", "features", "capacities"}
    assert isinstance(data["restricted"], bool)
    assert all(isinstance(on, bool) for on in data["features"].values())
    for capacity in data["capacities"].values():
        assert set(capacity) == {"limit", "used"}
        assert capacity["limit"] is None or isinstance(capacity["limit"], int)
        assert isinstance(capacity["used"], int)
