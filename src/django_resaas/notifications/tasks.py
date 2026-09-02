"""
Celery tasks. Deliberately thin - every task loads an id, delegates to a
service (engine/outbox_dispatcher/providers), and saves the result. No
business logic lives here that isn't also reachable from a management
command or a direct function call in a test.

Uses @shared_task (not a bound app instance) so this app stays usable by
any host project's own celery.py - see docs/django-resaas/features/
notifications.md for how a host project wires Celery + Beat.
"""

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from django_resaas.notifications.enums import ErrorType, OutboxStatus
from django_resaas.notifications.rendering import is_valid_e164, is_valid_email
from django_resaas.notifications.retry import (
    classify_exception,
    compute_backoff_seconds,
)

logger = logging.getLogger("django_resaas.notifications")


# =====================================================================
# WORKER
# =====================================================================


@shared_task(name="django_resaas.notifications.process_notification")
def process_notification(outbox_id):
    """Deliver exactly one NotificationOutbox row. Idempotent: a row
    already `sent`/`cancelled` short-circuits immediately (duplicate
    task execution is expected under at-least-once queueing, spec
    sections 47/98). Never reconstructs the business object - everything
    needed is already snapshotted on the Outbox row (spec section 37)."""

    from django_resaas.notifications.models import (
        NotificationDeliveryAttempt,
        NotificationOutbox,
    )
    from django_resaas.notifications.providers import NotificationProviderRegistry

    try:
        outbox = NotificationOutbox.objects.get(id=outbox_id)
    except NotificationOutbox.DoesNotExist:
        logger.warning("process_notification: outbox %s not found", outbox_id)
        return

    if outbox.status in (OutboxStatus.SENT, OutboxStatus.CANCELLED):
        return  # already delivered or cancelled - nothing to do

    claimed = NotificationOutbox.objects.filter(
        id=outbox_id,
        status__in=[OutboxStatus.QUEUED, OutboxStatus.PENDING, OutboxStatus.RETRY],
    ).update(status=OutboxStatus.PROCESSING, processing_at=timezone.now())

    if not claimed:
        return  # already claimed/processed by another worker

    outbox.refresh_from_db()

    attempt_number = outbox.attempts + 1

    attempt = NotificationDeliveryAttempt.objects.create(
        entity_id=outbox.entity_id,
        branch_id=outbox.branch_id,
        outbox=outbox,
        attempt_number=attempt_number,
        provider=outbox.provider,
    )

    # -----------------------------------------------------------
    # PERMANENT VALIDATION FAILURES - never worth a provider call
    # -----------------------------------------------------------

    invalid_reason = _invalid_recipient_reason(outbox)
    if invalid_reason:
        _finish_attempt(
            attempt,
            success=False,
            error_type=ErrorType.PERMANENT,
            error_message=invalid_reason,
        )
        _fail_outbox(outbox, invalid_reason)
        return

    provider = NotificationProviderRegistry.get(outbox.channel, outbox.provider)
    if provider is None:
        message = f"No provider registered for channel={outbox.channel!r} name={outbox.provider!r}"
        _finish_attempt(
            attempt,
            success=False,
            error_type=ErrorType.CONFIGURATION,
            error_message=message,
        )
        _fail_outbox(outbox, message)
        return

    # -----------------------------------------------------------
    # SEND
    # -----------------------------------------------------------

    try:
        result = provider.send(
            recipient=outbox.recipient_identity,
            subject=outbox.subject,
            body=outbox.body,
            metadata=outbox.provider_metadata,
            idempotency_key=outbox.idempotency_key,
        )
    except Exception as exc:
        outcome, error_type, message = classify_exception(exc)

        _finish_attempt(
            attempt, success=False, error_type=error_type, error_message=message
        )

        outbox.attempts = attempt_number

        if outcome == "retry" and outbox.attempts < outbox.max_attempts:
            outbox.transition(
                OutboxStatus.RETRY,
                last_error=message,
                next_retry_at=timezone.now()
                + timezone.timedelta(seconds=compute_backoff_seconds(outbox.attempts)),
            )
            outbox.save(
                update_fields=[
                    "status",
                    "attempts",
                    "last_error",
                    "next_retry_at",
                    "updated_at",
                ]
            )
        else:
            _fail_outbox(outbox, message, attempts=outbox.attempts)

        return

    # -----------------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------------

    attempt.success = True
    attempt.provider_message_id = result.get("provider_message_id")
    attempt.provider_status = result.get("provider_status")
    attempt.metadata = result.get("raw") or {}
    attempt.finished_at = timezone.now()
    attempt.save(
        update_fields=[
            "success",
            "provider_message_id",
            "provider_status",
            "metadata",
            "finished_at",
        ]
    )

    outbox.attempts = attempt_number
    outbox.transition(OutboxStatus.SENT, sent_at=timezone.now())
    outbox.save(update_fields=["status", "attempts", "sent_at", "updated_at"])


def _invalid_recipient_reason(outbox):
    from django_resaas.notifications.enums import Channel

    if outbox.channel == Channel.EMAIL and not is_valid_email(
        outbox.recipient_identity
    ):
        return f"Invalid email address: {outbox.recipient_identity!r}"

    if outbox.channel in (Channel.SMS, Channel.WHATSAPP) and not is_valid_e164(
        outbox.recipient_identity
    ):
        return f"Invalid E.164 phone number: {outbox.recipient_identity!r}"

    return None


def _finish_attempt(attempt, *, success, error_type=None, error_message=None):
    attempt.success = success
    attempt.error_type = error_type
    attempt.error_message = error_message
    attempt.finished_at = timezone.now()
    attempt.save(
        update_fields=["success", "error_type", "error_message", "finished_at"]
    )


def _fail_outbox(outbox, message, attempts=None):
    if attempts is not None:
        outbox.attempts = attempts

    outbox.transition(OutboxStatus.FAILED, failed_at=timezone.now(), last_error=message)
    outbox.save(
        update_fields=["status", "attempts", "failed_at", "last_error", "updated_at"]
    )

    with transaction.atomic():
        from django_resaas.notifications.engine import NotificationEngine

        NotificationEngine.create_fallback_outbox(outbox)


# =====================================================================
# PERIODIC (Celery Beat)
# =====================================================================


@shared_task(name="django_resaas.notifications.dispatch_pending_notifications")
def dispatch_pending_notifications():
    """The real guarantee of this system (spec section 33): finds
    pending/retry rows eligible right now and dispatches them, whether or
    not the fast on_commit path ever ran for them."""

    from django_resaas.notifications.outbox_dispatcher import OutboxDispatcher

    return OutboxDispatcher.dispatch_eligible_batch()


@shared_task(name="django_resaas.notifications.recover_stuck_notifications")
def recover_stuck_notifications():
    """Returns dispatcher/worker rows stuck past their timeout back to a
    recoverable state (spec sections 34-35)."""

    from django_resaas.notifications.outbox_dispatcher import OutboxDispatcher

    return OutboxDispatcher.recover_stuck()


@shared_task(name="django_resaas.notifications.cleanup_notifications")
def cleanup_notifications():
    """Conservative, opt-in retention cleanup (spec section 84) - deletes
    only `sent`/`failed`/`cancelled` rows older than the configured
    retention window. Never deletes anything still pending/queued/
    processing/retry/dispatching, regardless of age."""

    from django.conf import settings

    from django_resaas.notifications.models import (
        NotificationDeliveryAttempt,
        NotificationOutbox,
    )

    outbox_days = getattr(settings, "NOTIFICATION_OUTBOX_RETENTION_DAYS", 90)
    attempt_days = getattr(settings, "NOTIFICATION_ATTEMPT_RETENTION_DAYS", 90)

    outbox_cutoff = timezone.now() - timezone.timedelta(days=outbox_days)
    attempt_cutoff = timezone.now() - timezone.timedelta(days=attempt_days)

    deleted_attempts, _ = NotificationDeliveryAttempt.objects.filter(
        created_at__lt=attempt_cutoff
    ).delete()

    deleted_outboxes, _ = NotificationOutbox.objects.filter(
        status__in=[OutboxStatus.SENT, OutboxStatus.FAILED, OutboxStatus.CANCELLED],
        created_at__lt=outbox_cutoff,
    ).delete()

    return {"deleted_outboxes": deleted_outboxes, "deleted_attempts": deleted_attempts}
