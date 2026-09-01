from django.db import models
from django_resaas.core.base.models import TimeModel


class ManagedBy(models.TextChoices):
    DECORATOR = "decorator", "Decorator"
    MANUAL = "manual", "Manual"


class ModelExtraAction(TimeModel):

    # IDENTIDADE - these three together are the row's logical identity
    # (see the UniqueConstraint below), so a row missing any of them
    # isn't addressable in the first place.
    app = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    action = models.CharField(max_length=100)

    # UI
    label = models.CharField(max_length=150, null=True)
    icon = models.CharField(max_length=100, null=True, blank=True)
    tooltip = models.CharField(max_length=255, null=True, blank=True)
    position = models.CharField(max_length=20, null=True, blank=True)
    order = models.IntegerField(default=0)
    visible = models.BooleanField(default=True)

    autorequest = models.BooleanField(default=False)

    # API
    method = models.CharField(max_length=50, null=True)
    details = models.BooleanField(default=False)
    url = models.CharField(max_length=300, null=True)

    # PERMISSÃO - default to the safe assumption (not RESAAS-managed) for
    # any row created outside ActionSyncService (e.g. by hand, via the
    # admin). ActionSyncService always sets both of these explicitly for
    # actions it actually manages, so this only changes the default for
    # everyone else.
    permission = models.CharField(max_length=100, null=True)
    permission_managed = models.BooleanField(default=False)

    # GESTÃO
    managed_by = models.CharField(
        max_length=20,
        choices=ManagedBy.choices,
        default=ManagedBy.MANUAL,
    )

    class Meta:
        permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["app", "model", "action"],
                name="unique_model_extra_action",
            )
        ]

    class RESAAS:
        label_field = "action"

    def __str__(self):
        return f"{self.app}.{self.model} - {self.action}"