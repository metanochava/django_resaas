import uuid

from django.db import models

from django_saas.models.modulo import Modulo
from django_saas.models.entidade import Entidade
from django_saas.core.base.models import TimeModel
from django.contrib.contenttypes.models import ContentType


class EntidadeModelo(TimeModel):
    entidade = models.ForeignKey(Entidade, on_delete=models.CASCADE)
    modelo = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    class Meta:
        permissions = ()

    def __str__(self):
        return f'{self.entidade.nome} | {self.modelo.nome}'