from django.db import models

from django_resaas.engine.core.base.models import BaseModel


class Product(BaseModel):
    """
    Deliberately tiny - the point of this app is to demonstrate the
    framework's own conventions (multi-tenancy, soft delete, RESAAS schema),
    not to be a realistic product catalog.
    """

    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-created_at"]

    class RESAAS:
        label_field = "name"
        search_fields = ["name", "sku"]
        crud = True
        icon = "mdi-package-variant"

    def __str__(self):
        return self.name
