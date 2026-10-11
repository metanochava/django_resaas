"""A NotificationRule attached to a model lifecycle event
(core/events/lifecycle.py): the configurable side of lifecycle actions reuses
the notification engine - tenant-scoped rules, safe conditions, Outbox written
in the write's transaction, sent after the commit."""
import pytest

from dev.demo.models import Product
from django_resaas.notifications.enums import Category, Channel
from django_resaas.notifications.models import (
    NotificationOutbox, NotificationRule, NotificationSettings, NotificationTemplate,
)

pytestmark = pytest.mark.django_db

URL = "/api/demo/products/"


def _notifying_tenant(bootstrap_tenant, name):
    tenant = bootstrap_tenant(name, modules=("demo", "notifications"))
    # channels are off until the Entity configures them (opt-in)
    NotificationSettings.objects.create(entity=tenant["entity"], branch=None, email_enabled=True)
    tenant["client"].raise_request_exception = False
    return tenant


@pytest.fixture
def lifecycle_tenant(bootstrap_tenant, monkeypatch):
    monkeypatch.setattr(Product.RESAAS, "lifecycle_events", True, raising=False)
    return _notifying_tenant(bootstrap_tenant, "life-notif")


def _rule(tenant, event, conditions=None):
    rule = NotificationRule.objects.create(
        entity=tenant["entity"], branch=None, event=event, module="demo",
        channel=Channel.EMAIL, category=Category.TRANSACTIONAL, enabled=True,
        recipient_strategy="explicit", recipient_config={"email": "ops@example.com"},
        conditions=conditions or {},
    )
    NotificationTemplate.objects.create(
        entity=tenant["entity"], branch=None, rule=rule, language=None, subject="Product", body="Changed",
    )
    return rule


def test_each_update_is_one_notification(lifecycle_tenant):
    """occurrence_id is per write: two updates of the same product are two
    notifications, not one deduplicated by event + pk."""
    client = lifecycle_tenant["client"]
    rule = _rule(lifecycle_tenant, "demo.product.updated")
    pk = client.post(URL, {"name": "Widget", "sku": "W-1", "price": "10.00"}, format="json").json()["id"]

    for price in ("11.00", "12.00"):
        assert client.patch(f"{URL}{pk}/", {"price": price}, format="json").status_code == 200

    assert NotificationOutbox.objects.filter(rule=rule).count() == 2


def test_a_created_rule_does_not_fire_on_update(lifecycle_tenant):
    client = lifecycle_tenant["client"]
    rule = _rule(lifecycle_tenant, "demo.product.created")
    pk = client.post(URL, {"name": "Widget", "sku": "W-1", "price": "10.00"}, format="json").json()["id"]

    client.patch(f"{URL}{pk}/", {"price": "11.00"}, format="json")

    assert NotificationOutbox.objects.filter(rule=rule).count() == 1


def test_conditions_on_the_record_are_honoured(lifecycle_tenant):
    client = lifecycle_tenant["client"]
    rule = _rule(lifecycle_tenant, "demo.product.created", conditions={
        "all": [{"field": "object.sku", "operator": "==", "value": "VIP-1"}]
    })

    client.post(URL, {"name": "Plain", "sku": "P-1", "price": "1.00"}, format="json")
    client.post(URL, {"name": "Vip", "sku": "VIP-1", "price": "1.00"}, format="json")

    assert NotificationOutbox.objects.filter(rule=rule).count() == 1


def test_another_tenants_rule_never_fires(lifecycle_tenant, bootstrap_tenant):
    other = _notifying_tenant(bootstrap_tenant, "life-notif-other")
    foreign = _rule(other, "demo.product.created")

    lifecycle_tenant["client"].post(URL, {"name": "Widget", "sku": "W-1", "price": "10.00"}, format="json")

    assert NotificationOutbox.objects.filter(rule=foreign).count() == 0
