import uuid

from django.db import models

from django_resaas.models.modulo import Modulo
from django_resaas.models.entidade import Entidade
from django_resaas.core.base.models import TimeModel

class EntidadeModulo(TimeModel):
    entidade = models.ForeignKey(Entidade, on_delete=models.CASCADE)
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE)

    class Meta:
        permissions = ()

    def __str__(self):
        return f'{self.entidade.nome} | {self.modulo.nome}'