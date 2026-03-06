import uuid
from django.db import models
from django_saas.models.user import User
from django_saas.core.base.models import TimeModel

class UserLogin(TimeModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dispositivo = models.TextField(null=True)
    mobile = models.CharField(max_length=100, null=True)
    info = models.TextField(null=True)
    local_lat = models.CharField(max_length=100, null=True)
    local_lon = models.CharField(max_length=100, null=True)
    local_nome = models.CharField(max_length=100, null=True)
   
    is_blocked = models.BooleanField(default=False)

    class Meta:
        permissions = ()

    def __str__(self):
        return self.dispositivo or ''
