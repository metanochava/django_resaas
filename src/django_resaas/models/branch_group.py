
from django.db import models
from django.contrib.auth.models import Group
from django_resaas.core.base.models import TimeModel

class BranchGroup(TimeModel):
    branch = models.ForeignKey('django_resaas.Branch', on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("branch", "group")
        permissions = ()

    class RESAAS:
        label_field = "branch.name"
        # route="view_entity"

    def __str__(self):
        return f'{self.branch.name} | {self.group.name}'
