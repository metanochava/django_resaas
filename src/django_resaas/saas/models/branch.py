import uuid

from django.db import models
from django_resaas.saas.models.group import Group

from django_resaas.saas.core.base.models import BaseModel
from django_resaas.saas.models.address import Address
from django_resaas.saas.core.base.models import TimeModel


from django_resaas.saas.core.base.mixins.address import AddressMixin


def branch_photo_path(instance, file_name):
    return f'images/branches/{instance.id}/{file_name}'


class Branch(AddressMixin, TimeModel):
    name = models.CharField(max_length=100, null=True)
    entity = models.ForeignKey('django_resaas.Entity', on_delete=models.CASCADE)
    rodape = models.CharField(max_length=600, default='.', null=True)
    icon = models.CharField(max_length=100, default='.', null=True)
    label = models.CharField(max_length=100, default='.', null=True)

    # 📌 Shown on the location card (Google Maps InfoWindow) in
    # AddressLocationPicker.vue - also useful anywhere else a Branch
    # needs a thumbnail/summary (listings, etc.), not map-specific by
    # design.
    photo = models.ImageField(
        upload_to=branch_photo_path,
        null=True,
        blank=True,
        help_text='Shown on the map card and branch listings.',
    )

    description = models.TextField(
        null=True,
        blank=True,
        help_text='Shown on the map card and branch listings.',
    )

    # groups = models.ManyToManyField(Group, blank=True)

    class Meta:
        permissions = ()

    class RESAAS:
        label_field = "name"
        crud = True
        routes={
            'list': "list_branch",
            'view': "view_branch",
            'add': "add_branch",
            'change': "change_branch"
        }

    def __str__(self):
        return self.name or ''

