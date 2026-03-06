

from django.db import models
from django_resaas.core.base.models import TimeModel

class SucursalUser(TimeModel):

    sucursal = models.ForeignKey('django_resaas.Sucursal', on_delete=models.CASCADE)
    user = models.ForeignKey('django_resaas.User', on_delete=models.CASCADE)

    class Meta:
        permissions = ()

    def __str__(self):
        return f'{self.sucursal.nome} | {self.user.username}'
