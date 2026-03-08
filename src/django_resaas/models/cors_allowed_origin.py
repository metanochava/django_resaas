from django.db import models
from django_resaas.core.base.models import TimeModel

class CorsAllowedOrigin(TimeModel):
    origin = models.URLField(unique=True)
    def __str__(self):
        return self.origin