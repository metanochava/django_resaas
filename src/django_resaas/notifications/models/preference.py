from django.db import models

from django_resaas.engine.core.base.models import TimeModel
from django_resaas.notifications.enums import Category, Channel


class NotificationPreference(TimeModel):
    """A recipient's explicit choice for one (channel, category) pair.

    The recipient is NOT assumed to be a User - `recipient_type` +
    `recipient_key` is a generic, normalized identity (e.g.
    "user:<uuid>", "person:<uuid>", "email:foo@bar.com"), so any
    business app can register preferences for its own recipient kinds
    without django_resaas knowing about them.

    Consent semantics (enforced in notifications/engine.py, not here):
    - category == MARKETING requires an explicit enabled=True row to
      exist for (recipient, channel, category) - absence means "do not
      send", opt-in only.
    - Every other category is allowed by default in the absence of a
      row; an explicit enabled=False row is always an opt-out and is
      always respected, regardless of category.
    """

    entity = models.ForeignKey(
        "django_resaas.Entity",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    branch = models.ForeignKey(
        "django_resaas.Branch",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        null=True,
        blank=True,
    )

    recipient_type = models.CharField(max_length=100)

    recipient_key = models.CharField(max_length=255, db_index=True)

    channel = models.CharField(max_length=20, choices=Channel.choices)

    category = models.CharField(max_length=20, choices=Category.choices)

    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "entity",
                    "recipient_type",
                    "recipient_key",
                    "channel",
                    "category",
                ],
                name="unique_notification_preference",
            )
        ]

    class RESAAS:
        label_field = "recipient_key"
        crud = True

    def __str__(self):
        return f"{self.recipient_key} | {self.channel} | {self.category}"
