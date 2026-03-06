

from django.db import models
from django_resaas.core.base.models import TimeModel

class Modulo(TimeModel):
    nome = models.CharField(max_length=100, null=True)
    class Meta:
        permissions = ()

    def __str__(self):
        return self.nome
