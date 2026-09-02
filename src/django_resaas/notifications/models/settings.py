from django.db import models

from django_resaas.core.base.models import TimeModel


class NotificationSettings(TimeModel):
    """The System -> Entity -> Branch(optional) channel-enable layer.

    One row: the entity-wide default (branch=null). An optional second
    row per branch overrides it for that branch specifically. Both a
    channel's provider being configured (settings.py env vars) AND this
    row's corresponding *_enabled flag must be true for that channel to
    ever send anything for this entity/branch - "provider configured"
    never implies "channel active" (spec's opt-in principle, section 2).
    """

    entity = models.ForeignKey(
        "django_resaas.Entity",
        on_delete=models.CASCADE,
        related_name="notification_settings",
    )

    branch = models.ForeignKey(
        "django_resaas.Branch",
        on_delete=models.CASCADE,
        related_name="notification_settings",
        null=True,
        blank=True,
    )

    email_enabled = models.BooleanField(default=False)

    sms_enabled = models.BooleanField(default=False)

    whatsapp_enabled = models.BooleanField(default=False)

    # Entity-level language fallback tier (recipient language -> this ->
    # Django's LANGUAGE_CODE). Entity itself has no language field today;
    # this is where that tier lives instead - see notifications/rendering.py.
    default_language = models.ForeignKey(
        "django_resaas.Language",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["entity", "branch"],
                name="unique_notification_settings_entity_branch",
            )
        ]

    class RESAAS:
        label_field = "entity.name"
        crud = True

    def __str__(self):
        return f"{self.entity_id} | {self.branch_id or 'entity-wide'}"
