"""Spec sections 22-28, 90-91: the Outbox must be created inside the
caller's transaction, rolled back with it, and the provider must never
be called synchronously in the request/business-transaction path."""

import pytest
from django.db import transaction

from django_resaas.core.events import EventDispatcher
from django_resaas.notifications.enums import OutboxStatus
from django_resaas.notifications.models import NotificationOutbox
from django_resaas.notifications.outbox_dispatcher import OutboxDispatcher


def _emit(tenant):
    EventDispatcher.emit(
        "sales.sale.confirmed",
        entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id,
        actor=tenant["user"],
        context={"context_value": "x"},
    )


@pytest.mark.django_db
def test_rollback_of_business_transaction_removes_outbox(
    make_rule, notification_tenant
):
    make_rule(recipient_config={"email": "a@example.com"})

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            _emit(notification_tenant)
            assert (
                NotificationOutbox.objects.count() == 1
            )  # visible inside the transaction
            raise RuntimeError("simulated business failure after outbox creation")

    assert NotificationOutbox.objects.count() == 0  # gone after rollback


@pytest.mark.django_db
def test_provider_never_called_synchronously(
    make_rule, notification_tenant, fake_providers
):
    make_rule(recipient_config={"email": "a@example.com"})

    _emit(notification_tenant)

    assert fake_providers["email"].sent == []  # never called inline, no queue ran yet

    outbox = NotificationOutbox.objects.get()
    assert outbox.status == OutboxStatus.PENDING


@pytest.mark.django_db(transaction=True)
def test_on_commit_dispatches_after_real_commit(
    make_rule, notification_tenant, monkeypatch
):
    """transaction.on_commit only fires on a REAL commit - this test uses
    transaction=True (a real TransactionTestCase-style test) specifically
    to exercise that, unlike every other test in this app which stays
    inside the default rolled-back test transaction on purpose."""

    make_rule(recipient_config={"email": "a@example.com"})

    delayed = []
    monkeypatch.setattr(
        "django_resaas.notifications.tasks.process_notification.delay",
        lambda outbox_id: delayed.append(outbox_id),
    )

    with transaction.atomic():
        _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    assert str(outbox.id) in delayed
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.QUEUED


@pytest.mark.django_db(transaction=True)
def test_broker_down_leaves_outbox_recoverable_not_lost(
    make_rule, notification_tenant, monkeypatch
):
    """spec sections 28/68: broker unreachable after commit must not lose
    the notification - the row must come back to `pending`."""

    make_rule(recipient_config={"email": "a@example.com"})

    def _boom(outbox_id):
        raise ConnectionError("broker unreachable")

    monkeypatch.setattr(
        "django_resaas.notifications.tasks.process_notification.delay", _boom
    )

    with transaction.atomic():
        _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    assert outbox.status == OutboxStatus.PENDING  # never stuck in "dispatching"


@pytest.mark.django_db
def test_two_concurrent_claims_only_one_succeeds(make_rule, notification_tenant):
    """The atomic conditional UPDATE claim (spec sections 29-30): two
    callers racing on the same row - the second one is a no-op."""

    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)
    outbox = NotificationOutbox.objects.get()

    first = NotificationOutbox.objects.filter(
        id=outbox.id, status__in=[OutboxStatus.PENDING, OutboxStatus.RETRY]
    ).update(status=OutboxStatus.DISPATCHING)
    second = NotificationOutbox.objects.filter(
        id=outbox.id, status__in=[OutboxStatus.PENDING, OutboxStatus.RETRY]
    ).update(status=OutboxStatus.DISPATCHING)

    assert first == 1
    assert second == 0
