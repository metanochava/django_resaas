from django.db import models
from django_resaas.engine.core.base.models import BaseModel



class Payroll(BaseModel):
    period = models.ForeignKey(
        'hr.PayrollPeriod',
        on_delete=models.CASCADE,
        related_name='payrolls'
    )

    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='payrolls'
    )

    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('processed', 'Processed'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft'
    )

    class Meta:
        unique_together = ('period', 'employee')
        ordering = ['employee']

    class RESAAS:
        label_field = "employee.person.full_name"
        search_fields = ["employee.person.full_name"]
        crud = True

    def __str__(self):
        return f"{self.employee} - {self.period}"