import uuid

from django.db import models
from django_saas.models.tipo_entidade import TipoEntidade
from django_saas.core.base.models import TimeModel
from django.contrib.contenttypes.models import ContentType


class TipoEntidadeModelo(TimeModel):
    tipo_entidade = models.ForeignKey(TipoEntidade, on_delete=models.CASCADE)
    modelo = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    class Meta:
        permissions = ()

    def __str__(self):
        return f'{self.tipo_entidade.nome} | {self.modelo.name}'