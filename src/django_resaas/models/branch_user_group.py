
from django.db import models

from django_resaas.core.base.models import TimeModel


class BranchUserGroup(TimeModel):
    branch = models.ForeignKey('django_resaas.Branch', on_delete=models.CASCADE)
    user = models.ForeignKey('django_resaas.User', on_delete=models.CASCADE)
    group = models.ForeignKey('django_resaas.Group', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('branch', 'user', 'group')
        permissions = ()

    class RESAAS:
        label_field = "branch.name"
        # route="view_entity"
    def __str__(self):
        return f'{self.user.username} | {self.branch.name} | {self.group.name}'
