"""Spec sections 32, 34-35, 52, 90: periodic recovery finds eligible
pending/retry rows, ignores future-scheduled ones, and un-sticks rows
whose dispatching/processing timed out - without ever touching a row
that's genuinely still in flight within the timeout window."""

import pytest
from django.utils import timezone

from django_resaas.core.events import EventDispatcher
from django_resaas.notifications.enums import OutboxStatus
from django_resaas.notifications.models import NotificationOutbox
from django_resaas.notifications.outbox_dispatcher import OutboxDispatcher

pytestmark = pytest.mark.django_db


def _emit(tenant, scheduled_at=None, **context):
    EventDispatcher.emit(
        "sales.sale.confirmed",
        entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id,
        actor=tenant["user"],
        context={"context_value": "x", **context},
        scheduled_at=scheduled_at,
    )


def test_scheduled_future_is_ignored_by_recovery(
    make_rule, notification_tenant, monkeypatch
):
    monkeypatch.setattr(
        OutboxDispatcher, "_enqueue_or_release", classmethod(lambda cls, oid: None)
    )

    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    outbox.scheduled_at = timezone.now() + timezone.timedelta(hours=1)
    outbox.save(update_fields=["scheduled_at"])

    dispatched = OutboxDispatcher.dispatch_eligible_batch()

    assert dispatched == 0
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.PENDING


def test_scheduled_past_is_dispatched(make_rule, notification_tenant, monkeypatch):
    monkeypatch.setattr(
        OutboxDispatcher, "_enqueue_or_release", classmethod(lambda cls, oid: None)
    )

    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    outbox.scheduled_at = timezone.now() - timezone.timedelta(minutes=1)
    outbox.save(update_fields=["scheduled_at"])

    OutboxDispatcher.dispatch_eligible_batch()

    outbox.refresh_from_db()
    assert (
        outbox.status == OutboxStatus.DISPATCHING
    )  # claimed (enqueue itself is a no-op here)


def test_emit_scheduled_at_flows_to_outbox_and_is_ignored_by_recovery(
    make_rule, notification_tenant, monkeypatch
):
    """EventDispatcher.emit(scheduled_at=...) - not just a post-creation
    edit of the Outbox row - is what a caller actually uses to request a
    delayed send (e.g. "remind tomorrow at 08:00")."""

    monkeypatch.setattr(
        OutboxDispatcher, "_enqueue_or_release", classmethod(lambda cls, oid: None)
    )

    make_rule(recipient_config={"email": "a@example.com"})
    future = timezone.now() + timezone.timedelta(hours=1)
    _emit(notification_tenant, scheduled_at=future)

    outbox = NotificationOutbox.objects.get()
    assert outbox.scheduled_at == future

    dispatched = OutboxDispatcher.dispatch_eligible_batch()

    assert dispatched == 0
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.PENDING


def test_emit_without_scheduled_at_defaults_to_now(make_rule, notification_tenant):
    """No regression: the common case (no scheduled_at passed) still
    gets an immediately-eligible row, exactly as before this was wired
    through emit()."""

    make_rule(recipient_config={"email": "a@example.com"})
    before = timezone.now()
    _emit(notification_tenant)
    after = timezone.now()

    outbox = NotificationOutbox.objects.get()
    assert before <= outbox.scheduled_at <= after


def test_next_retry_at_in_future_is_ignored(
    make_rule, notification_tenant, monkeypatch
):
    monkeypatch.setattr(
        OutboxDispatcher, "_enqueue_or_release", classmethod(lambda cls, oid: None)
    )

    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    # Direct update, not .transition(): this is test setup simulating "a
    # retry is already scheduled for later", not a validated state
    # transition a real code path would perform in one step.
    NotificationOutbox.objects.filter(id=outbox.id).update(
        status=OutboxStatus.RETRY,
        next_retry_at=timezone.now() + timezone.timedelta(minutes=5),
    )

    dispatched = OutboxDispatcher.dispatch_eligible_batch()

    assert dispatched == 0


def test_recover_stuck_dispatching(make_rule, notification_tenant, settings):
    settings.OUTBOX_DISPATCH_TIMEOUT = 60

    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    outbox.transition(OutboxStatus.DISPATCHING)
    outbox.dispatching_at = timezone.now() - timezone.timedelta(seconds=120)
    outbox.save()

    recovered = OutboxDispatcher.recover_stuck()

    assert recovered == 1
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.PENDING


def test_recent_dispatching_is_not_touched(make_rule, notification_tenant, settings):
    settings.OUTBOX_DISPATCH_TIMEOUT = 300

    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    outbox.transition(OutboxStatus.DISPATCHING)
    outbox.save()  # dispatching_at defaults to "now" via try_dispatch normally; here just now

    recovered = OutboxDispatcher.recover_stuck()

    assert recovered == 0


def test_recover_stuck_processing_moves_to_retry(
    make_rule, notification_tenant, settings
):
    settings.OUTBOX_PROCESSING_TIMEOUT = 60

    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    outbox.transition(OutboxStatus.DISPATCHING)
    outbox.transition(OutboxStatus.QUEUED)
    outbox.transition(OutboxStatus.PROCESSING)
    outbox.processing_at = timezone.now() - timezone.timedelta(seconds=120)
    outbox.save()

    recovered = OutboxDispatcher.recover_stuck()

    assert recovered == 1
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.RETRY
