import uuid

from django.db import models

from django_resaas.engine.models.app import App
from django_resaas.engine.models.entity import Entity
from django_resaas.engine.core.base.models import TimeModel

class EntityApp(TimeModel):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    app = models.ForeignKey(App, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("entity", "app")
        permissions = ()
    class RESAAS:
        label_field = "entity.name"

    def __str__(self):
        return f'{self.entity.name} | {self.app.name}'