from django.db import models
from django_resaas.engine.core.base.models import BaseModel



class EmployeeSalary(BaseModel):
    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='salaries'
    )

    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-effective_date']

    class RESAAS:
        label_field = "employee.person.full_name"
        search_fields = ["employee.person.full_name"]
        crud = True

    def __str__(self):
        return f"{self.employee} - {self.base_salary}"