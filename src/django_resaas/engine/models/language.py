import uuid
from django.db import models
from django_resaas.engine.core.base.models import TimeModel

class Language(TimeModel):

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        permissions = ()

    class RESAAS:
        label_field = "name"
        # route="view_entity"

    def __str__(self):
        return self.name
