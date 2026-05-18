from django.db import models
from django_resaas.core.base.models import BaseModel

class EmployeeSpecialty(BaseModel):
    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='employee_specialties'
    )

    specialty = models.ForeignKey(
        'hr.Specialty',
        on_delete=models.CASCADE,
        related_name='employee_specialties'
    )

    class Meta:
        unique_together = ('employee', 'specialty')

    def __str__(self):
        return f"{self.employee} - {self.specialty}"