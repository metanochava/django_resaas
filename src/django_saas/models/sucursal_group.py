
from django.db import models
from django.contrib.auth.models import Group
from django_saas.core.base.models import TimeModel

class SucursalGroup(TimeModel):
    sucursal = models.ForeignKey('django_saas.Sucursal', on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("sucursal", "group")
        permissions = ()

    def __str__(self):
        return f'{self.sucursal.nome} | {self.group.name}'
