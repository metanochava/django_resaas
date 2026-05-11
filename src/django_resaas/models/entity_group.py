import uuid

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django_resaas.core.base.models import TimeModel


class EntityGroup(TimeModel):
    entity = models.ForeignKey('django_resaas.Entity', on_delete=models.CASCADE)
    group = models.ForeignKey('django_resaas.Group', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ("entity", "group")
        permissions = ()
    class RESAAS:
        label_field = "entity.name"

    def __str__(self):
        return f'{self.entity.name} | {self.group.name}'

