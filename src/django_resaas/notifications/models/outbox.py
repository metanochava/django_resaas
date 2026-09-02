from django.db import models
from django.utils import timezone

from django_resaas.core.base.models import BaseModel
from django_resaas.notifications.enums import (
    Category,
    Channel,
    OutboxStatus,
    Priority,
    VALID_TRANSITIONS,
)
from django_resaas.notifications.exceptions import InvalidTransitionError


def assert_transition(old_status, new_status):
    """Raise InvalidTransitionError unless enums.VALID_TRANSITIONS allows
    old_status -> new_status. Centralizing this is what stops e.g. a
    'sent' row from ever silently going back to 'processing'."""

    allowed = VALID_TRANSITIONS.get(old_status, set())

    if new_status not in allowed:
        raise InvalidTransitionError(
            f"NotificationOutbox cannot transition {old_status!r} -> {new_status!r}"
        )


class NotificationOutbox(BaseModel):
    """A durable, at-least-once intention to send one notification.

    Extends BaseModel (not TimeModel like the config models) on purpose:
    an Outbox row is always created from an already fully tenant-scoped
    business event (the triggering object already has entity+branch), so
    BaseModel's "entity and branch both required" contract is exactly
    right here - unlike NotificationRule/Template/Preference/Settings.

    This row - not Celery, not the broker - is the system's source of
    truth. It must be created inside the same transaction.atomic() block
    as the business change that triggered it (see notifications/engine.py).
    """

    event = models.CharField(max_length=150, db_index=True)

    rule = models.ForeignKey(
        "notifications.NotificationRule",
        on_delete=models.SET_NULL,
        null=True,
        related_name="outbox_entries",
    )

    channel = models.CharField(max_length=20, choices=Channel.choices)

    category = models.CharField(max_length=20, choices=Category.choices)

    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.NORMAL
    )

    recipient_type = models.CharField(max_length=100)

    # Resolved address snapshot (email / E.164 phone) - not a FK, the
    # recipient's live data may change after this row is created.
    recipient_identity = models.CharField(max_length=255)

    recipient_reference = models.CharField(max_length=255, null=True, blank=True)

    # Rendered snapshot - the worker sends exactly this, it never
    # re-renders the template (spec section 11).
    subject = models.CharField(max_length=500, null=True, blank=True)

    body = models.TextField()

    provider = models.CharField(max_length=50, null=True, blank=True)

    # Non-secret only - never provider API keys/tokens (spec section 19).
    provider_metadata = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20,
        choices=OutboxStatus.choices,
        default=OutboxStatus.PENDING,
        db_index=True,
    )

    idempotency_key = models.CharField(max_length=255, unique=True)

    deduplication_key = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )

    scheduled_at = models.DateTimeField(default=timezone.now, db_index=True)

    queued_at = models.DateTimeField(null=True, blank=True)
    dispatching_at = models.DateTimeField(null=True, blank=True)
    processing_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)

    attempts = models.PositiveIntegerField(default=0)

    max_attempts = models.PositiveIntegerField(default=5)

    last_error = models.TextField(null=True, blank=True)

    # Includes {"object": {"app_label", "model", "pk"}, "occurrence_id",
    # "actor_id"} - everything the worker might want to log, but never
    # anything it needs to re-fetch the business object with.
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
            models.Index(fields=["status", "next_retry_at"]),
            models.Index(fields=["entity", "status"]),
            models.Index(fields=["channel"]),
            models.Index(fields=["provider"]),
            models.Index(fields=["created_at"]),
        ]

    class RESAAS:
        label_field = "event"
        crud = True

    def __str__(self):
        return f"{self.event} | {self.channel} | {self.status}"

    def transition(self, new_status, **fields):
        """Validate + apply a status change in one place. Callers still
        decide *which* extra fields to set (sent_at, last_error, ...)."""

        assert_transition(self.status, new_status)

        self.status = new_status

        for field, value in fields.items():
            setattr(self, field, value)
