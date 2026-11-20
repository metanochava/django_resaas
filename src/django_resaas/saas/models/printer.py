from django.db import models

from django_resaas.saas.core.base.models import BaseModel
from django_resaas.saas.core.printing.formats import PAPER_CHOICES


class Printer(BaseModel):
    """A printer of a Branch (BaseModel: entity + branch from the context):
    its paper and the documents it prints by default there
    (core/printing). Each document has at most one default printer per Branch
    (PrinterSerializer). The physical choice of printer stays the browser's
    or a device's; this says which paper each document comes out on."""

    name = models.CharField(max_length=80)
    paper_format = models.CharField(max_length=20, choices=PAPER_CHOICES, default="thermal_80")
    documents = models.JSONField(default=list, blank=True,
                                 help_text="The document codes this printer prints by default, e.g. sales.receipt")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Printer"
        verbose_name_plural = "Printers"

    class RESAAS:
        label_field = "name"
        search_fields = ["name"]
        crud = True

    def __str__(self):
        return self.name
