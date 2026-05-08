import uuid

from django.db import models

from django_resaas.models.app import App
from django_resaas.models.entity import Entity
from django_resaas.core.base.models import TimeModel

class EntityApp(TimeModel):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    app = models.ForeignKey(App, on_delete=models.CASCADE)

    class Meta:
        permissions = ()
    class RESAAS:
        label_field = "entity.name"

    def __str__(self):
        return f'{self.entity.name} | {self.app.name}'