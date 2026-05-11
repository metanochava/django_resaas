import uuid

from django.db import models
from django.contrib.auth.models import Permission

class Group(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=150,
        unique=True
    )

    editable = models.BooleanField()

    permissions = models.ManyToManyField(
        Permission,
        blank=True
    )


    class Meta:
        verbose_name = 'group'
        verbose_name_plural = 'groups'

    def __str__(self):
        return self.name