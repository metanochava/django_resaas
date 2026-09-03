"""Spec section 88/64: nothing here may ever cross tenants, including
the "global" recovery task."""

import pytest

from django_resaas.engine.core.events import EventDispatcher
from django_resaas.notifications.enums import Channel
from django_resaas.notifications.models import NotificationOutbox, NotificationRule
from django_resaas.notifications.outbox_dispatcher import OutboxDispatcher

pytestmark = pytest.mark.django_db


def test_rule_from_entity_a_does_not_fire_for_entity_b(
    make_rule, notification_tenant, bootstrap_tenant, activate_module
):
    make_rule(recipient_config={"email": "a@example.com"})

    tenant_b = bootstrap_tenant("tenant-b-user", modules=("sales",))
    from django_resaas.notifications.models import NotificationSettings

    NotificationSettings.objects.create(entity=tenant_b["entity"], email_enabled=True)

    EventDispatcher.emit(
        "sales.sale.confirmed",
        entity_id=tenant_b["entity"].id,
        branch_id=tenant_b["branch"].id,
        actor=tenant_b["user"],
        context={"context_value": "x"},
    )

    assert NotificationOutbox.objects.count() == 0


def test_outbox_scoped_to_its_own_entity(
    make_rule, notification_tenant, bootstrap_tenant
):
    make_rule(recipient_config={"email": "a@example.com"})

    EventDispatcher.emit(
        "sales.sale.confirmed",
        entity_id=notification_tenant["entity"].id,
        branch_id=notification_tenant["branch"].id,
        actor=notification_tenant["user"],
        context={"context_value": "x"},
    )

    outbox = NotificationOutbox.objects.get()
    assert outbox.entity_id == notification_tenant["entity"].id


def test_recovery_never_mixes_tenants(
    make_rule, notification_tenant, bootstrap_tenant, monkeypatch
):
    """dispatch_eligible_batch() is a global task, but every row it finds
    still carries its own entity/branch - simulate two tenants each with
    one pending outbox and confirm each keeps its own entity."""

    monkeypatch.setattr(
        "django_resaas.notifications.outbox_dispatcher.OutboxDispatcher._enqueue_or_release",
        classmethod(lambda cls, outbox_id: None),  # no real broker in tests
    )

    rule = make_rule(recipient_config={"email": "a@example.com"})

    tenant_b = bootstrap_tenant("tenant-b-recovery", modules=("sales",))
    from django_resaas.notifications.models import NotificationSettings

    NotificationSettings.objects.create(entity=tenant_b["entity"], email_enabled=True)

    rule_b = NotificationRule.objects.create(
        entity=tenant_b["entity"],
        event="sales.sale.confirmed",
        module="sales",
        channel=Channel.EMAIL,
        enabled=True,
        recipient_strategy="explicit",
        recipient_config={"email": "b@example.com"},
    )
    from django_resaas.notifications.models import NotificationTemplate

    NotificationTemplate.objects.create(
        rule=rule_b, entity=tenant_b["entity"], body="hi"
    )

    EventDispatcher.emit(
        "sales.sale.confirmed",
        entity_id=notification_tenant["entity"].id,
        branch_id=notification_tenant["branch"].id,
        actor=notification_tenant["user"],
        context={"context_value": "x"},
    )
    EventDispatcher.emit(
        "sales.sale.confirmed",
        entity_id=tenant_b["entity"].id,
        branch_id=tenant_b["branch"].id,
        actor=tenant_b["user"],
        context={"context_value": "x"},
    )

    assert NotificationOutbox.objects.count() == 2

    OutboxDispatcher.dispatch_eligible_batch()

    by_entity = {o.entity_id: o for o in NotificationOutbox.objects.all()}
    assert notification_tenant["entity"].id in by_entity
    assert tenant_b["entity"].id in by_entity
