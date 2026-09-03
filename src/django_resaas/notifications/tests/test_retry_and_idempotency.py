"""Spec sections 41-47, 93-98: temporary errors retry with backoff up to
max_attempts, permanent/configuration errors fail immediately, duplicate
events/tasks never produce duplicate sends."""

import pytest

from django_resaas.engine.core.events import EventDispatcher
from django_resaas.notifications.enums import ErrorType, OutboxStatus
from django_resaas.notifications.exceptions import (
    ProviderPermanentError,
    ProviderTemporaryError,
)
from django_resaas.notifications.models import (
    NotificationDeliveryAttempt,
    NotificationOutbox,
)
from django_resaas.notifications.tasks import process_notification

pytestmark = pytest.mark.django_db


def _emit(tenant):
    EventDispatcher.emit(
        "sales.sale.confirmed",
        entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id,
        actor=tenant["user"],
        context={"context_value": "x"},
    )


def test_temporary_error_moves_to_retry_with_backoff(
    make_rule, notification_tenant, fake_providers
):
    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    fake_providers["email"].fail_with = ProviderTemporaryError("timeout")

    process_notification(str(outbox.id))

    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.RETRY
    assert outbox.attempts == 1
    assert outbox.next_retry_at is not None

    attempt = NotificationDeliveryAttempt.objects.get(outbox=outbox, attempt_number=1)
    assert attempt.success is False
    assert attempt.error_type == ErrorType.TEMPORARY


def test_permanent_error_fails_without_retry(
    make_rule, notification_tenant, fake_providers
):
    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    fake_providers["email"].fail_with = ProviderPermanentError("rejected")

    process_notification(str(outbox.id))

    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.FAILED
    assert outbox.next_retry_at is None

    attempt = NotificationDeliveryAttempt.objects.get(outbox=outbox, attempt_number=1)
    assert attempt.error_type == ErrorType.PERMANENT


def test_max_attempts_stops_retrying(
    make_rule, notification_tenant, fake_providers, settings
):
    settings.OUTBOX_MAX_ATTEMPTS = (
        2  # max_attempts is snapshotted onto the Outbox at creation
    )

    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    fake_providers["email"].fail_with = ProviderTemporaryError("timeout")

    process_notification(str(outbox.id))
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.RETRY
    assert outbox.attempts == 1

    process_notification(str(outbox.id))  # claim allows RETRY -> PROCESSING directly
    outbox.refresh_from_db()

    assert outbox.status == OutboxStatus.FAILED  # attempts (2) == max_attempts (2)
    assert outbox.attempts == 2


def test_success_marks_sent_and_records_attempt(
    make_rule, notification_tenant, fake_providers
):
    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    process_notification(str(outbox.id))

    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.SENT
    assert outbox.sent_at is not None
    assert len(fake_providers["email"].sent) == 1

    attempt = NotificationDeliveryAttempt.objects.get(outbox=outbox, attempt_number=1)
    assert attempt.success is True
    assert attempt.provider_message_id


def test_duplicate_event_creates_one_outbox(make_rule, notification_tenant):
    make_rule(recipient_config={"email": "a@example.com"})

    _emit(notification_tenant)
    _emit(
        notification_tenant
    )  # same event, no occurrence_id given -> same default occurrence

    assert NotificationOutbox.objects.count() == 1


def test_duplicate_task_execution_calls_provider_once(
    make_rule, notification_tenant, fake_providers
):
    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()

    process_notification(str(outbox.id))
    process_notification(
        str(outbox.id)
    )  # simulates the queue redelivering the same task

    assert len(fake_providers["email"].sent) == 1
    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.SENT


def test_sent_outbox_task_is_a_no_op(make_rule, notification_tenant, fake_providers):
    make_rule(recipient_config={"email": "a@example.com"})
    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    process_notification(str(outbox.id))
    assert len(fake_providers["email"].sent) == 1

    # A late/duplicate delivery of the *same* task after it's already sent.
    process_notification(str(outbox.id))
    assert len(fake_providers["email"].sent) == 1
