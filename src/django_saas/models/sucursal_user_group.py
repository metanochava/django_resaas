
from django.db import models

from django_saas.core.base.models import TimeModel


class SucursalUserGroup(TimeModel):
    sucursal = models.ForeignKey('django_saas.Sucursal', on_delete=models.CASCADE)
    user = models.ForeignKey('django_saas.User', on_delete=models.CASCADE)
    group = models.ForeignKey('auth.Group', on_delete=models.CASCADE)

    class Meta:
        permissions = ()

    def __str__(self):
        return f'{self.user.username} | {self.sucursal.nome} | {self.group.name}'
