from django.db import models


class TwoFactorPolicy(models.TextChoices):
    """The two-factor rule of ONE level (EntityType, Entity, EntityUser).
    INHERIT = no opinion here, follow the level above. See
    core/services/two_factor_service.py for how the levels combine."""

    INHERIT = "inherit", "Inherit"
    DISABLED = "disabled", "Disabled"
    OPTIONAL = "optional", "Optional"
    REQUIRED = "required", "Required"


def policy_field():
    return models.CharField(
        verbose_name="Two-factor policy",
        max_length=10,
        choices=TwoFactorPolicy.choices,
        default=TwoFactorPolicy.INHERIT,
        help_text=(
            "Two-factor authentication at this level. A REQUIRED level above can "
            "never be weakened by the levels below it."
        ),
    )
