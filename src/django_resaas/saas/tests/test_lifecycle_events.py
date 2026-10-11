"""Model lifecycle events (core/events/lifecycle.py): the generic CRUD of
BaseAPIView emits "<app>.<model>.<action>" through the EventDispatcher, in the
transaction of the write, for models with RESAAS.lifecycle_events. Exercised on
the framework's neutral demo app (dev.demo), never on a business module."""
import pytest
from django.db import transaction
from rest_framework.test import APIClient

from dev.demo.models import Category, Product
from django_resaas.saas.core.events import EventDispatcher
from django_resaas.saas.core.events.lifecycle import (
    lifecycle_actions_for, lifecycle_event_catalogue, load_instance,
)
from django_resaas.saas.tests.test_permission_api_security import _actor

pytestmark = pytest.mark.django_db

URL = "/api/demo/products/"
BODY = {"name": "Widget", "sku": "W-1", "price": "10.00"}


@pytest.fixture
def events(monkeypatch):
    """Only this test's listeners (the notification engine's "*" is set aside)."""
    monkeypatch.setattr(EventDispatcher, "_listeners", [])
    received = []
    EventDispatcher.register("demo.*", received.append)
    return received


@pytest.fixture
def opt_in(monkeypatch):
    def apply(value=True, model=Product):
        monkeypatch.setattr(model.RESAAS, "lifecycle_events", value, raising=False)
    apply()
    return apply


def _tenant(bootstrap_tenant, name):
    tenant = bootstrap_tenant(name, modules=("demo",))
    tenant["client"].raise_request_exception = False
    return tenant


def _create(client):
    response = client.post(URL, BODY, format="json")
    assert response.status_code == 201, response.content
    return response.json()["id"]


def _names(received):
    return [payload["event"] for payload in received]


# ------------------------------------------------------------------ each action

def test_create_emits_created_only_with_the_signed_context(bootstrap_tenant, events, opt_in):
    tenant = _tenant(bootstrap_tenant, "life-create")

    pk = _create(tenant["client"])

    assert _names(events) == ["demo.product.created"]
    payload = events[0]
    assert payload["object"] == {"app_label": "demo", "model": "product", "pk": pk}
    assert payload["entity_id"] == str(tenant["entity"].id)
    assert payload["branch_id"] == str(tenant["branch"].id)
    assert payload["actor_id"] == str(tenant["user"].id)
    assert payload["context"] == {"lifecycle": "created"}


def test_update_emits_updated_not_created_and_lists_the_fields(bootstrap_tenant, events, opt_in):
    tenant = _tenant(bootstrap_tenant, "life-update")
    pk = _create(tenant["client"])
    events.clear()

    response = tenant["client"].patch(f"{URL}{pk}/", {"price": "12.50"}, format="json")

    assert response.status_code == 200
    assert _names(events) == ["demo.product.updated"]
    assert events[0]["context"] == {"lifecycle": "updated", "fields": ["price"]}


def test_delete_restore_and_hard_delete_emit_their_own_events(bootstrap_tenant, events, opt_in):
    tenant = _tenant(bootstrap_tenant, "life-delete")
    client = tenant["client"]
    pk = _create(client)
    events.clear()

    assert client.delete(f"{URL}{pk}/").status_code in (200, 204)
    assert _names(events) == ["demo.product.deleted"]
    assert load_instance(events[-1]).deleted_at is not None  # soft-deleted rows are found

    assert client.post(f"{URL}{pk}/restore/").status_code == 202
    assert _names(events)[-1] == "demo.product.restored"

    assert client.delete(f"{URL}{pk}/hard_delete/").status_code == 200
    assert _names(events)[-1] == "demo.product.hard_deleted"
    assert events[-1]["object"]["pk"] == pk
    assert load_instance(events[-1]) is None
    assert not Product.all_objects.filter(pk=pk).exists()


def test_every_write_is_its_own_occurrence(bootstrap_tenant, events, opt_in):
    """Notification idempotency keys use occurrence_id: two updates of the same
    record must not look like one."""
    tenant = _tenant(bootstrap_tenant, "life-occurrence")
    pk = _create(tenant["client"])

    for price in ("11.00", "12.00"):
        tenant["client"].patch(f"{URL}{pk}/", {"price": price}, format="json")

    occurrences = [payload["occurrence_id"] for payload in events]
    assert len(occurrences) == 3 and len(set(occurrences)) == 3


# ------------------------------------------------------------------ opt-in

def test_a_model_that_did_not_opt_in_emits_nothing(bootstrap_tenant, events, opt_in):
    tenant = _tenant(bootstrap_tenant, "life-optout")

    response = tenant["client"].post("/api/demo/categories/", {"name": "Tools"}, format="json")

    assert response.status_code == 201
    assert lifecycle_actions_for(Category) == set()
    assert events == []


def test_only_the_listed_actions_are_emitted(bootstrap_tenant, events, opt_in):
    opt_in(["created"])
    tenant = _tenant(bootstrap_tenant, "life-subset")
    pk = _create(tenant["client"])

    tenant["client"].patch(f"{URL}{pk}/", {"price": "9.00"}, format="json")
    tenant["client"].delete(f"{URL}{pk}/")

    assert _names(events) == ["demo.product.created"]


def test_an_unknown_action_is_a_configuration_error(opt_in):
    opt_in(["created", "saved"])

    with pytest.raises(ValueError, match="saved"):
        lifecycle_actions_for(Product)


# ------------------------------------------------------------------ order and failures

def test_listeners_run_in_registration_order(bootstrap_tenant, monkeypatch, opt_in):
    monkeypatch.setattr(EventDispatcher, "_listeners", [])
    order = []
    EventDispatcher.register("demo.product.created", lambda payload: order.append("first"))
    EventDispatcher.register("demo.*", lambda payload: order.append("second"))
    tenant = _tenant(bootstrap_tenant, "life-order")

    _create(tenant["client"])

    assert order == ["first", "second"]


def test_a_propagating_listener_failure_rolls_the_write_back(bootstrap_tenant, monkeypatch, opt_in):
    monkeypatch.setattr(EventDispatcher, "_listeners", [])

    def broken(payload):
        raise RuntimeError("rule broken")

    EventDispatcher.register("demo.product.created", broken, propagate=True)
    tenant = _tenant(bootstrap_tenant, "life-rollback")

    response = tenant["client"].post(URL, BODY, format="json")

    assert response.status_code == 500
    assert not Product.all_objects.filter(sku="W-1").exists()


def test_a_non_propagating_listener_failure_keeps_the_write(bootstrap_tenant, monkeypatch, opt_in):
    monkeypatch.setattr(EventDispatcher, "_listeners", [])

    def broken(payload):
        raise RuntimeError("audit sink down")

    EventDispatcher.register("demo.product.created", broken)
    tenant = _tenant(bootstrap_tenant, "life-keep")

    assert tenant["client"].post(URL, BODY, format="json").status_code == 201
    assert Product.objects.filter(sku="W-1").exists()


def test_external_effects_wait_for_the_commit(bootstrap_tenant, monkeypatch, opt_in, django_capture_on_commit_callbacks):
    """A listener defers its external effect with transaction.on_commit: it
    runs after the commit, never inside the write."""
    monkeypatch.setattr(EventDispatcher, "_listeners", [])
    sent = []
    EventDispatcher.register(
        "demo.product.created",
        lambda payload: transaction.on_commit(lambda: sent.append(payload["object"]["pk"])),
    )
    tenant = _tenant(bootstrap_tenant, "life-commit")

    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        pk = _create(tenant["client"])
        assert sent == []

    assert len(callbacks) == 1
    callbacks[0]()
    assert sent == [pk]


def test_nothing_is_deferred_when_the_write_is_rolled_back(bootstrap_tenant, monkeypatch, opt_in, django_capture_on_commit_callbacks):
    monkeypatch.setattr(EventDispatcher, "_listeners", [])
    EventDispatcher.register("demo.product.created", lambda payload: transaction.on_commit(lambda: None))

    def broken(payload):
        raise RuntimeError("rule broken")

    EventDispatcher.register("demo.product.created", broken, propagate=True)
    tenant = _tenant(bootstrap_tenant, "life-commit-rollback")

    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        assert tenant["client"].post(URL, BODY, format="json").status_code == 500

    assert callbacks == []


# ------------------------------------------------------------------ security

def test_no_permission_no_write_no_event(bootstrap_tenant, events, opt_in):
    tenant = _tenant(bootstrap_tenant, "life-perm")
    client = _actor(tenant, "life-perm-actor")  # a group with no permission

    assert client.post(URL, BODY, format="json").status_code == 403
    assert events == []


def test_the_tenant_comes_from_the_context_not_the_body(bootstrap_tenant, events, opt_in):
    tenant = _tenant(bootstrap_tenant, "life-tenant-a")
    other = _tenant(bootstrap_tenant, "life-tenant-b")

    response = tenant["client"].post(
        URL, {**BODY, "entity": str(other["entity"].id), "branch": str(other["branch"].id)}, format="json"
    )

    assert response.status_code == 201
    assert events[0]["entity_id"] == str(tenant["entity"].id)
    assert Product.objects.get(pk=events[0]["object"]["pk"]).entity_id == tenant["entity"].id


def test_load_instance_never_crosses_tenants(bootstrap_tenant, events, opt_in):
    tenant = _tenant(bootstrap_tenant, "life-load-a")
    other = _tenant(bootstrap_tenant, "life-load-b")
    _create(tenant["client"])
    payload = events[0]

    assert load_instance(payload) is not None
    assert load_instance({**payload, "entity_id": str(other["entity"].id)}) is None
    assert load_instance({**payload, "entity_id": None}) is None


def test_a_request_without_context_is_refused_before_any_event(bootstrap_tenant, events, opt_in):
    tenant = _tenant(bootstrap_tenant, "life-nocontext")
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=tenant["user"])

    assert client.post(URL, BODY, format="json").status_code == 403
    assert events == []


# ------------------------------------------------------------------ catalogue

def test_the_catalogue_lists_the_opted_in_events(opt_in):
    opt_in(["created", "updated"])

    catalogue = lifecycle_event_catalogue()

    assert "demo.product.created" in catalogue
    assert "demo.product.updated" in catalogue
    assert "demo.product.deleted" not in catalogue
    assert not any(name.startswith("demo.category.") for name in catalogue)


def test_the_notification_catalog_offers_lifecycle_events_of_active_modules_only(bootstrap_tenant, opt_in):
    active = bootstrap_tenant("life-catalog-on", modules=("demo",))
    inactive = bootstrap_tenant("life-catalog-off")

    on = active["client"].get("/api/notifications/catalog/").json()
    off = inactive["client"].get("/api/notifications/catalog/").json()

    assert "demo.product.created" in on["lifecycle_events"]
    assert not any(name.startswith("demo.") for name in off["lifecycle_events"])
