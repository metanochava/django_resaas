from django.db import models

from django_resaas.core.base.models import BaseModel
from django_resaas.notifications.enums import ErrorType


class NotificationDeliveryAttempt(BaseModel):
    """One historical record per attempt to deliver a NotificationOutbox.

    Extends BaseModel for the same reason NotificationOutbox does - it is
    always created from an already tenant-scoped Outbox row.
    """

    outbox = models.ForeignKey(
        "notifications.NotificationOutbox",
        on_delete=models.CASCADE,
        related_name="delivery_attempts",
    )

    attempt_number = models.PositiveIntegerField()

    provider = models.CharField(max_length=50, null=True, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)

    finished_at = models.DateTimeField(null=True, blank=True)

    # null = still in progress, True/False = final result of this attempt.
    success = models.BooleanField(null=True)

    provider_message_id = models.CharField(max_length=255, null=True, blank=True)

    provider_status = models.CharField(max_length=100, null=True, blank=True)

    error_type = models.CharField(
        max_length=20, choices=ErrorType.choices, null=True, blank=True
    )

    error_message = models.TextField(null=True, blank=True)

    # Sanitized provider raw response only - never secrets/tokens.
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["outbox", "attempt_number"],
                name="unique_notification_delivery_attempt",
            )
        ]

    class RESAAS:
        label_field = "outbox.event"
        crud = True

    def __str__(self):
        return f"{self.outbox_id} #{self.attempt_number}"
