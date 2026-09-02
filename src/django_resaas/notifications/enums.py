from django.db import models


class Channel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    WHATSAPP = "whatsapp", "WhatsApp"


class Category(models.TextChoices):
    TRANSACTIONAL = "transactional", "Transactional"
    SECURITY = "security", "Security"
    REMINDER = "reminder", "Reminder"
    SYSTEM = "system", "System"
    MARKETING = "marketing", "Marketing"


class Priority(models.TextChoices):
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class OutboxStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DISPATCHING = "dispatching", "Dispatching"
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    RETRY = "retry", "Retry"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class ErrorType(models.TextChoices):
    TEMPORARY = "temporary", "Temporary"
    PERMANENT = "permanent", "Permanent"
    CONFIGURATION = "configuration", "Configuration"


# Status transitions considered valid by assert_transition() in
# notifications/models/outbox.py. Anything not listed here is rejected -
# this is what stops e.g. "sent" from ever going back to "processing".
VALID_TRANSITIONS = {
    OutboxStatus.PENDING: {OutboxStatus.DISPATCHING, OutboxStatus.CANCELLED},
    OutboxStatus.DISPATCHING: {
        OutboxStatus.QUEUED,
        OutboxStatus.PENDING,  # enqueue failed (broker down) - fall back
        OutboxStatus.RETRY,
        OutboxStatus.CANCELLED,
    },
    OutboxStatus.QUEUED: {
        OutboxStatus.PROCESSING,
        OutboxStatus.PENDING,
        OutboxStatus.CANCELLED,  # manual cancel (retry_notification action) before the worker claims it
    },
    OutboxStatus.PROCESSING: {
        OutboxStatus.SENT,
        OutboxStatus.RETRY,
        OutboxStatus.FAILED,
    },
    OutboxStatus.RETRY: {
        OutboxStatus.DISPATCHING,
        OutboxStatus.PENDING,
        OutboxStatus.FAILED,
        OutboxStatus.CANCELLED,
    },
    OutboxStatus.SENT: set(),
    # A manual retry (admin action) is the one deliberate way out of
    # "failed" - never automatic, that would defeat max_attempts.
    OutboxStatus.FAILED: {OutboxStatus.PENDING},
    OutboxStatus.CANCELLED: set(),
}
