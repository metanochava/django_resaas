from django.db import models

from django_resaas.engine.core.base.models import TimeModel
from django_resaas.notifications.enums import Category, Channel, Priority


class NotificationRule(TimeModel):
    """A single (event, channel) wiring: who gets notified, under what
    conditions, through which channel, using which template.

    Deliberately extends TimeModel (not BaseModel): BaseModel.branch is
    mandatory, but this model's tenant hierarchy is "Entity required,
    Branch optional" (a null branch means "applies to every branch of
    this entity") - see the plan's "Desvios explícitos" section.
    """

    entity = models.ForeignKey(
        "django_resaas.Entity",
        on_delete=models.CASCADE,
        related_name="notification_rules",
    )

    branch = models.ForeignKey(
        "django_resaas.Branch",
        on_delete=models.CASCADE,
        related_name="notification_rules",
        null=True,
        blank=True,
    )

    event = models.CharField(max_length=150, db_index=True)

    # Owning business module of `event` (e.g. "sales" for
    # "sales.sale.confirmed") - checked against EntityApp exactly like any
    # other module-gated resource in this framework before this rule is
    # ever considered.
    module = models.CharField(max_length=100)

    channel = models.CharField(max_length=20, choices=Channel.choices)

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.TRANSACTIONAL,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )

    # Opt-in by construction: a rule that nobody has explicitly enabled
    # sends nothing, no matter what else is configured.
    enabled = models.BooleanField(default=False)

    recipient_strategy = models.CharField(max_length=50)

    recipient_config = models.JSONField(default=dict, blank=True)

    # {"all": [...]}/{"any": [...]} - see notifications/conditions.py.
    conditions = models.JSONField(default=dict, blank=True)

    # Explicit provider override; null = use the channel's registered
    # default provider.
    provider = models.CharField(max_length=50, null=True, blank=True)

    # Off by default - never fall back to another channel (extra cost)
    # without an explicit opt-in per rule.
    fallback_channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        null=True,
        blank=True,
        default=None,
    )

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["entity", "event", "channel"]),
            models.Index(fields=["module"]),
        ]

    class RESAAS:
        label_field = "event"
        crud = True

    def __str__(self):
        return f"{self.event} | {self.channel}"
