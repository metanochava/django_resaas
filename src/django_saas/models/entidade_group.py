import uuid

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django_saas.core.base.models import TimeModel


class EntidadeGroup(TimeModel):
    entidade = models.ForeignKey('django_saas.Entidade', on_delete=models.CASCADE)
    group = models.ForeignKey('auth.Group', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ("entidade", "group")
        permissions = ()

    def __str__(self):
        return f'{self.entidade.nome} | {self.group.name}'

