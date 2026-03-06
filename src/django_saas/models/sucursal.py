import uuid

from django.db import models
from django.contrib.auth.models import Group

from django_saas.core.base.models import BaseModel
from django_saas.models.endereco import Endereco
from django_saas.core.base.models import TimeModel


class Sucursal(TimeModel):
    nome = models.CharField(max_length=100, null=True)

    entidade = models.ForeignKey('django_saas.Entidade', on_delete=models.CASCADE)
    endereco = models.ForeignKey(Endereco, on_delete=models.SET_NULL, null=True, blank=True)

    rodape = models.CharField(max_length=600, default='.', null=True)
    icon = models.CharField(max_length=100, default='.', null=True)
    label = models.CharField(max_length=100, default='.', null=True)

    # groups = models.ManyToManyField(Group, blank=True)

    class Meta:
        permissions = ()

    def __str__(self):
        return self.nome or ''

