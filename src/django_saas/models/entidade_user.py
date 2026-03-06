import uuid

from django.db import models
from django.contrib.contenttypes.models import ContentType

from django_saas.models.user import User
from django_saas.models.entidade import Entidade
from django_saas.core.base.models import TimeModel

class EntidadeUser(TimeModel):

    entidade = models.ForeignKey(Entidade, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        permissions = ()

    def __str__(self):
        return f'{self.entidade.nome} | {self.user.username}'