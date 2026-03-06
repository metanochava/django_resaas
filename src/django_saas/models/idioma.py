import uuid
from django.db import models
from django_saas.core.base.models import TimeModel

class Idioma(TimeModel):

    nome = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        permissions = ()

    def __str__(self):
        return self.nome
