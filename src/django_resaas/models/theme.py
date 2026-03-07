import uuid
from django.db import models
from django_resaas.core.base.models import TimeModel


class Theme(TimeModel):

    nome = models.CharField(max_length=100)

    primary = models.CharField(max_length=7, default="#1976D2")
    secondary = models.CharField(max_length=7, default="#26A69A")
    accent = models.CharField(max_length=7, default="#9C27B0")

    positive = models.CharField(max_length=7, default="#21BA45")
    negative = models.CharField(max_length=7, default="#C10015")
    warning = models.CharField(max_length=7, default="#F2C037")
    info = models.CharField(max_length=7, default="#31CCEC")

    dark = models.CharField(max_length=7, default="#1d1d1d")

    def to_dict(self):
        return {
            "primary": self.primary,
            "secondary": self.secondary,
            "accent": self.accent,
            "positive": self.positive,
            "negative": self.negative,
            "warning": self.warning,
            "info": self.info,
            "dark": self.dark,
        }
    class Meta:
        verbose_name = 'Theme'
        verbose_name_plural = 'Theme'
        permissions = ()
        

    def __str__(self):
        return self.primary