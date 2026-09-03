import uuid

from django.db import models
from django.contrib.contenttypes.models import ContentType

from django_resaas.engine.models.user import User
from django_resaas.engine.models.entity import Entity
from django_resaas.engine.core.base.models import TimeModel

class EntityUser(TimeModel):

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("entity", "user")
        permissions = ()
    class RESAAS:
        label_field = "entity.name"
        
    def __str__(self):
        return f'{self.entity.name} | {self.user.username}'