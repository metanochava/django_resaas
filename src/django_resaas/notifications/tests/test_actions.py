"""Spec sections 59-61, 78: manual retry/cancel go through permission-
checked actions, never a generic PATCH; a `sent` row can never be
cancelled; a non-`failed` row can never be manually retried."""

import pytest

from django_resaas.engine.core.events import EventDispatcher
from django_resaas.notifications.enums import OutboxStatus
from django_resaas.notifications.models import NotificationOutbox

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _grant_outbox_action_permissions(notification_tenant):
    """`retry`/`cancel` are custom @resaas_action permissions
    (`retry_notificationoutbox`/`cancel_notificationoutbox`).

    Two things have to happen before "Root" can use them, neither of
    which the normal test-session migration does:

    1. ActionSyncService.sync_registry() has to actually run *after*
       django_resaas.notifications.views has been imported (that's what
       populates VIEW_REGISTRY with the `retry`/`cancel` actions in the
       first place) - the one-time post_migrate sync that created the
       test database ran *before* any URL ever got resolved, so
       VIEW_REGISTRY was still empty and these two Permission rows were
       never created at all (see `manage.py sync_actions`, the real
       command for this - it has the exact same "VIEW_REGISTRY must
       already be populated" precondition). This is a pre-existing
       repo-wide characteristic of @resaas_action, not new here.
    2. Even once the Permission rows exist, ActionSyncService never
       grants custom-action permissions to any group automatically
       (unlike bootstrap_tenant's standard CRUD permissions) - granting
       them is a deliberate, separate admin step in this framework.
    """

    import django_resaas.notifications.views  # noqa: F401 - populate VIEW_REGISTRY
    from django.contrib.auth.models import Permission
    from django_resaas.engine.core.base.registry import VIEW_REGISTRY
    from django_resaas.engine.core.services.action_sync_service import ActionSyncService

    ActionSyncService.sync_registry(VIEW_REGISTRY)

    permissions = Permission.objects.filter(
        codename__in=["retry_notificationoutbox", "cancel_notificationoutbox"]
    )
    notification_tenant["root_group"].permissions.add(*permissions)


def _emit(tenant):
    EventDispatcher.emit(
        "sales.sale.confirmed",
        entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id,
        actor=tenant["user"],
        context={"context_value": "x"},
    )


def test_generic_patch_is_blocked(make_rule, notification_tenant):
    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)
    outbox = NotificationOutbox.objects.get()

    client = notification_tenant["client"]
    response = client.patch(
        f"/api/notifications/outbox/{outbox.id}/", {"status": "sent"}
    )

    assert response.status_code == 405
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.PENDING


def test_generic_create_is_blocked(notification_tenant):
    client = notification_tenant["client"]
    response = client.post("/api/notifications/outbox/", {})
    assert response.status_code == 405


def test_cancel_pending_outbox(make_rule, notification_tenant):
    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)
    outbox = NotificationOutbox.objects.get()

    client = notification_tenant["client"]
    response = client.post(f"/api/notifications/outbox/{outbox.id}/cancel/")

    assert response.status_code == 200
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.CANCELLED


def test_cannot_cancel_sent_outbox(make_rule, notification_tenant):
    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)
    outbox = NotificationOutbox.objects.get()
    outbox.transition(OutboxStatus.DISPATCHING)
    outbox.transition(OutboxStatus.QUEUED)
    outbox.transition(OutboxStatus.PROCESSING)
    outbox.transition(OutboxStatus.SENT)
    outbox.save()

    client = notification_tenant["client"]
    response = client.post(f"/api/notifications/outbox/{outbox.id}/cancel/")

    assert response.status_code == 400
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.SENT


def test_retry_only_valid_from_failed(make_rule, notification_tenant):
    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)
    outbox = NotificationOutbox.objects.get()  # still "pending"

    client = notification_tenant["client"]
    response = client.post(f"/api/notifications/outbox/{outbox.id}/retry/")

    assert response.status_code == 400


def test_retry_from_failed_resets_to_pending(make_rule, notification_tenant):
    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)
    outbox = NotificationOutbox.objects.get()
    outbox.transition(OutboxStatus.DISPATCHING)
    outbox.transition(OutboxStatus.QUEUED)
    outbox.transition(OutboxStatus.PROCESSING)
    outbox.transition(OutboxStatus.FAILED, last_error="boom")
    outbox.save()

    client = notification_tenant["client"]
    response = client.post(f"/api/notifications/outbox/{outbox.id}/retry/")

    assert response.status_code == 200
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.PENDING
    assert outbox.last_error is None
