from django.db import models

from django_resaas.core.base.models import TimeModel


class NotificationTemplate(TimeModel):
    """A rendered-per-language message template for one NotificationRule.

    Same structural reasoning as NotificationRule: TimeModel + explicit
    entity/branch (branch optional), not BaseModel.
    """

    entity = models.ForeignKey(
        "django_resaas.Entity",
        on_delete=models.CASCADE,
        related_name="notification_templates",
    )

    branch = models.ForeignKey(
        "django_resaas.Branch",
        on_delete=models.CASCADE,
        related_name="notification_templates",
        null=True,
        blank=True,
    )

    rule = models.ForeignKey(
        "notifications.NotificationRule",
        on_delete=models.CASCADE,
        related_name="templates",
    )

    # null = the rule's default/fallback template (used when no template
    # matches the resolved recipient language).
    language = models.ForeignKey(
        "django_resaas.Language",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    subject = models.CharField(max_length=500, null=True, blank=True)

    body = models.TextField()

    enabled = models.BooleanField(default=True)

    # e.g. {"provider_template_name": "...", "provider_template_id": "...",
    # "provider_language": "..."} for channels whose provider requires
    # pre-approved templates (WhatsApp Cloud API, some SMS gateways).
    provider_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["rule", "language"],
                name="unique_notification_template_rule_language",
            )
        ]

    class RESAAS:
        label_field = "rule.event"
        crud = True

    def __str__(self):
        lang = self.language.code if self.language_id else "default"
        return f"{self.rule_id} | {lang}"
