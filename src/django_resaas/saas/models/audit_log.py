from django.db import models

from django_resaas.saas.models.user import User

from django_resaas.saas.core.base.models import TimeModel

class AuditLog(TimeModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)
    model = models.CharField(max_length=105)
    object_id = models.CharField(max_length=100)
    # request context of the event (both optional: shell/commands have none)
    entity = models.ForeignKey('django_resaas.Entity', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    class RESAAS:
        label_field = "action"
        crud = True
        routes={
            'list': "list_auditlog",
            'view': "view_auditlog",
            'add': "add_auditlog",
            'change': "change_auditlog"
        }
