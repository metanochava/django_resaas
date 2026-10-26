from django.db import models

from django_resaas.saas.core.base.models import TimeModel
from django_resaas.notifications.crypto import decrypt_config, encrypt_config
from django_resaas.notifications.enums import Channel


class NotificationProviderCredential(TimeModel):
    """A channel's provider credentials, at one of three levels:

    - branch override: entity + branch;
    - entity-wide override: entity, branch null - e.g. a hospital's own
      WhatsApp Business number/token;
    - platform default: entity null and branch null - what every tenant
      without an override uses. Managed only at platform level
      (PlatformNotificationProviderCredentialAPIView, Root).

    When no active row matches, the env vars (EMAIL_*, TWILIO_*, ...) are
    the last fallback.

    Nothing here is stored in plaintext: `config` (the plain provider-
    specific credential dict, e.g. {"account_sid": ..., "auth_token":
    ..., "from_number": ...} for Twilio) only ever exists in memory -
    set_config()/get_config() encrypt/decrypt it through
    `encrypted_config` via notifications/crypto.py. Resolution order:
    see notifications/tenant_credentials.py.
    """

    entity = models.ForeignKey(
        "django_resaas.Entity",
        on_delete=models.CASCADE,
        related_name="notification_provider_credentials",
        null=True,
        blank=True,
    )

    branch = models.ForeignKey(
        "django_resaas.Branch",
        on_delete=models.CASCADE,
        related_name="notification_provider_credentials",
        null=True,
        blank=True,
    )

    channel = models.CharField(max_length=20, choices=Channel.choices)

    # Must match a registered provider's `.name` for this channel (e.g.
    # "twilio", "meta_cloud_api", "firebase") - which shape `config` has.
    provider_name = models.CharField(max_length=50)

    encrypted_config = models.TextField()

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["entity", "branch", "channel"],
                name="unique_notification_provider_credential_entity_branch_channel",
            ),
            # NULLs are distinct in the constraint above: one platform
            # default per channel needs its own
            models.UniqueConstraint(
                fields=["channel"],
                condition=models.Q(entity__isnull=True),
                name="unique_notification_provider_credential_platform_channel",
            ),
            # a branch override always belongs to an Entity
            models.CheckConstraint(
                condition=models.Q(entity__isnull=False) | models.Q(branch__isnull=True),
                name="notification_provider_credential_branch_needs_entity",
            ),
        ]

    class RESAAS:
        label_field = "provider_name"
        crud = True

    def __str__(self):
        if self.entity_id is None:
            return f"platform | {self.channel}"
        return f"{self.entity_id} | {self.branch_id or 'entity-wide'} | {self.channel}"

    def set_config(self, config: dict):
        self.encrypted_config = encrypt_config(config)

    def get_config(self) -> dict:
        return decrypt_config(self.encrypted_config)
