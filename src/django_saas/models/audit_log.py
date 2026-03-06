from django.db import models

from django_saas.models.user import User
from django_saas.models.entidade import Entidade
from django_saas.models.sucursal import Sucursal
from django_saas.core.base.models import TimeModel

class AuditLog(TimeModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)
    model = models.CharField(max_length=105)
    object_id = models.CharField(max_length=100)



class Testee(TimeModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )