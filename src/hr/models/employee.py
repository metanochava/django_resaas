from django.db import models
from django_resaas.core.base.models import BaseModel


class Employee(BaseModel):
    # =========================
    # 🔗 RELATIONSHIPS
    # =========================
    person = models.ForeignKey(
        'django_resaas.Person',
        on_delete=models.CASCADE,
        related_name='employees'
    )

    manager = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subordinates'
    )

    # =========================
    # 🏷️ CORE FIELDS
    # =========================
    code = models.CharField(max_length=50)
    position = models.CharField(max_length=100)

    # =========================
    # 📅 DATES
    # =========================
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)


    # =========================
    # 🔐 META
    # =========================
    class Meta:
        unique_together =('person', 'branch'),

    # =========================
    # 🧠 STRING REPRESENTATION
    # =========================
    def __str__(self):
        return f"{self.person.full_name} ({self.position})"