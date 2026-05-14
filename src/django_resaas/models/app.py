

from django.db import models
from django_resaas.core.base.models import TimeModel

class App(TimeModel):
    name = models.CharField(max_length=100, null=True)
    class Meta:
        permissions = ()

    class RESAAS:
        label_field = "name"
        crud = True
        routes={
            'list': "add_app",
            'view': "view_app",
            'add': "add_app",
            'change': "change_app"
        }

    def __str__(self):
        return self.name
