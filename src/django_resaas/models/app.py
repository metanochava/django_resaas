

from django.db import models
from django_resaas.core.base.models import TimeModel

class App(TimeModel):
    name = models.CharField(max_length=100, null=True)
    class Meta:
        permissions = ()

    class RESAAS:
        label_field = "name"
        # route="view_entity"

    def __str__(self):
        return self.name
