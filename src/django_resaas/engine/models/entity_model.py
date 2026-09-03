import uuid

from django.db import models

from django_resaas.engine.models.app import App
from django_resaas.engine.models.entity import Entity
from django_resaas.engine.core.base.models import TimeModel
from django.contrib.contenttypes.models import ContentType


class EntityModel(TimeModel):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    model = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("entity", "model")
        permissions = ()

    class RESAAS:
        label_field = "entity.name"
        
    def __str__(self):
        return f'{self.entity.name} | {self.model.name}'