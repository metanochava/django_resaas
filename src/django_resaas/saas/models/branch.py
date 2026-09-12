import uuid

from django.db import models
from django_resaas.saas.models.group import Group

from django_resaas.saas.core.base.models import BaseModel
from django_resaas.saas.models.address import Address
from django_resaas.saas.core.base.models import TimeModel


class Branch(TimeModel):
    name = models.CharField(max_length=100, null=True)
    address = models.OneToOneField( 'django_resaas.Address', on_delete=models.SET_NULL,  null=True, blank=True, related_name='branch', help_text='Main address of the branch.')
    entity = models.ForeignKey('django_resaas.Entity', on_delete=models.CASCADE)


    rodape = models.CharField(max_length=600, default='.', null=True)
    icon = models.CharField(max_length=100, default='.', null=True)
    label = models.CharField(max_length=100, default='.', null=True)

    # groups = models.ManyToManyField(Group, blank=True)

    class Meta:
        permissions = ()

    class RESAAS:
        label_field = "name"
        crud = True
        routes={
            'list': "add_banch",
            'view': "view_banch",
            'add': "add_banch",
            'change': "change_banch"
        }

    def __str__(self):
        return self.name or ''

