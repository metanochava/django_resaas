from django.db import models

from django_resaas.models.user import User

from django_resaas.core.base.models import TimeModel

class AuditLog(TimeModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)
    model = models.CharField(max_length=105)
    object_id = models.CharField(max_length=100)
    class RESAAS:
        label_field = "name"
        crud = True
        routes={
            'list': "add_auditlog",
            'view': "view_auditlog",
            'add': "add_auditlog",
            'change': "change_auditlog"
        }
