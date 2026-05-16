import uuid

from django.db import models
from django_resaas.models.entity_type import EntityType
from django_resaas.core.base.models import TimeModel
from django.contrib.contenttypes.models import ContentType


class EntityTypeModel(TimeModel):
    entity_type = models.ForeignKey(EntityType, on_delete=models.CASCADE)
    model = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("entity_type", "model")
        permissions = ()

    class RESAAS:
        label_field = "entity_type.name"
        

    def __str__(self):
        return f'{self.entity_type.name} | {self.model.name}'