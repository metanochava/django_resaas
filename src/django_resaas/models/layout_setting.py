import uuid
from django.db import models
from django_resaas.core.base.models import TimeModel

class LayoutSetting(TimeModel):
    primary = models.CharField(max_length=50, null=True, blank=True, default="")
    secondary = models.CharField(max_length=50, null=True, blank=True, default="")
    accent = models.CharField(max_length=50, null=True, blank=True, default="")
    dark = models.CharField(max_length=50, null=True, blank=True, default="")
    positive = models.CharField(max_length=50, null=True, blank=True, default="")
    negative = models.CharField(max_length=50, null=True, blank=True, default="")
    info = models.CharField(max_length=50, null=True, blank=True, default="")
    warning = models.CharField(max_length=50, null=True, blank=True, default="")

    class Meta:
        verbose_name = 'LayoutSetting'
        verbose_name_plural = 'LayoutSettings'
        permissions = ()
        

    def __str__(self):
        return self.primary
      
