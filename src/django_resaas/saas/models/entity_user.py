import uuid

from django.db import models

from django_resaas.saas.models.two_factor_policy import policy_field
from django.contrib.contenttypes.models import ContentType

from django_resaas.saas.models.user import User
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.core.base.models import TimeModel

class EntityUser(TimeModel):

    # two-factor rule of this level (see TwoFactorPolicy / two_factor_service)
    two_factor_policy = policy_field()

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("entity", "user")
        permissions = ()
    class RESAAS:
        label_field = "entity.name"
        
    def __str__(self):
        return f'{self.entity.name} | {self.user.username}'