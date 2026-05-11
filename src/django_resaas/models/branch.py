import uuid

from django.db import models
from django_resaas.models.group import Group

from django_resaas.core.base.models import BaseModel
from django_resaas.models.address import Address
from django_resaas.core.base.models import TimeModel


class Branch(TimeModel):
    name = models.CharField(max_length=100, null=True)

    entity = models.ForeignKey('django_resaas.Entity', on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)

    rodape = models.CharField(max_length=600, default='.', null=True)
    icon = models.CharField(max_length=100, default='.', null=True)
    label = models.CharField(max_length=100, default='.', null=True)

    # groups = models.ManyToManyField(Group, blank=True)

    class Meta:
        permissions = ()

    class RESAAS:
        label_field = "branch.name"
        # route="view_entity"


    def __str__(self):
        return self.name or ''

