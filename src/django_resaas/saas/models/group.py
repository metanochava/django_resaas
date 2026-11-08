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

    editable = models.BooleanField(default=False)

    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='resaas_groups'  # 🔥 ESSENCIAL
    )

    # app labels of the modules whose menu this profile does not show
    # (UserAPIView.menus). Only the menu: the permissions stay what they are.
    hidden_menu_apps = models.JSONField(default=list, blank=True)

    # permission codenames whose menu entries this profile does not show
    # (core/menus.py menu_roles). Only the menu: the permission stays granted.
    hidden_menu_permissions = models.JSONField(default=list, blank=True)


    class Meta:
        verbose_name = 'group'
        verbose_name_plural = 'groups'

    def __str__(self):
        return self.name