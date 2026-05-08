import uuid
from django.db import models
from django_resaas.models.language import Language
from django_resaas.core.base.models import TimeModel


class Translation(TimeModel):
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    chave = models.TextField(null=True, blank=True)
    translation = models.TextField(null=True, blank=True)

    class Meta:
        permissions = ()

    class RESAAS:
        label_field = "language"
        route="view_translation"

    def __str__(self):
        return self.chave or ''
