
from django.db import models

from django_resaas.saas.core.base.models import TimeModel


ACTIVE = "Active"
INACTIVE = "Inactive"


class BranchUserGroup(TimeModel):
    """A user's profile (Group) in a Branch. Only an Active, not deleted
    assignment grants access (permissions, context, menus, profile choice,
    notifications); the Admin switches it on and off (users/{id}/groupState/).
    A new assignment is Active."""
    branch = models.ForeignKey('django_resaas.Branch', on_delete=models.CASCADE)
    user = models.ForeignKey('django_resaas.User', on_delete=models.CASCADE)
    group = models.ForeignKey('django_resaas.Group', on_delete=models.CASCADE)
    state = models.CharField(
        default=ACTIVE,
        choices=((INACTIVE, INACTIVE), (ACTIVE, ACTIVE)),
    )

    class Meta:
        unique_together = ('branch', 'user', 'group')
        permissions = ()

    class RESAAS:
        label_field = "branch.name"
        # route="view_entity"
    def __str__(self):
        return f'{self.user.username} | {self.branch.name} | {self.group.name}'
