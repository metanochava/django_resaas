from django.db import models
from django_resaas.core.base.models import BaseModel


class Contract(BaseModel):
    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='contracts'
    )

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    salary = models.DecimalField(max_digits=12, decimal_places=2)

    contract_type = models.CharField(
        max_length=50,
        choices=[
            ('full_time', 'Full Time'),
            ('part_time', 'Part Time'),
            ('temporary', 'Temporary')
        ],
        default='full_time'
    )

    class Meta:
        ordering = ['-start_date']

    class RESAAS:
        label_field = "employee.person.full_name"
        search_fields = ["employee.person.full_name", "contract_type"]
        crud = True

    def __str__(self):
        return f"{self.employee} - {self.contract_type}"