from django.db import models
from django_resaas.core.base.models import TimeModel


class ModelExtraAction(TimeModel):

    # IDENTIDADE
    app = models.CharField(max_length=100, null=True)
    model = models.CharField(max_length=100, null=True)
    action = models.CharField(max_length=100, null=True)

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

    # PERMISSÃO
    permission = models.CharField(max_length=100, null=True)
    permission_managed = models.BooleanField(default=True)

    # GESTÃO
    managed_by = models.CharField(max_length=20, default="decorator")

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