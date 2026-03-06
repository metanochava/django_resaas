import uuid
from django.db import models
from django_saas.models.idioma import Idioma
from django_saas.core.base.models import TimeModel


class Traducao(TimeModel):
    idioma = models.ForeignKey(Idioma, on_delete=models.CASCADE)
    chave = models.TextField(null=True, blank=True)
    traducao = models.TextField(null=True, blank=True)

    class Meta:
        permissions = ()

    def __str__(self):
        return self.chave or ''
