
from django.db import models
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django_saas.core.base.models import TimeModel

def icon_path(instance, file_name):
    return f'{instance.nome}/{file_name}'


class TipoEntidade(TimeModel):
    nome = models.CharField(max_length=100, null=True)
    icon = models.FileField(upload_to=icon_path, default='logo.png', blank=True)
    license = models.TextField(default='license')
    label = models.CharField(max_length=100, null=True)
    ordem = models.IntegerField(default=2)
    crair_entidade = models.BooleanField(null=True, default=True)

    class Meta:
        permissions = ()

    def __str__(self):
        return self.nome

