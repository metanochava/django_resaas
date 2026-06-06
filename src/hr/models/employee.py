from django.db import models
from django.core.exceptions import ValidationError

from django_resaas.core.base.models import BaseModel


class Employee(BaseModel):

    # ==========================================
    # RELATIONSHIPS
    # ==========================================

    person = models.ForeignKey(
        'django_resaas.Person',
        on_delete=models.CASCADE,
        related_name='employees'
    )

    manager = models.ForeignKey(
        'hr.Employee',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subordinates'
    )

    position = models.ForeignKey(
        'hr.JobPosition',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='employees'
    )

    # ==========================================
    # CORE FIELDS
    # ==========================================

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True
    )

    # ==========================================
    # DATES
    # ==========================================

    hire_date = models.DateField()

    termination_date = models.DateField(
        null=True,
        blank=True
    )

    # ==========================================
    # VALIDATIONS
    # ==========================================

    def clean(self):

        super().clean()

        if self.manager and self.manager == self:

            raise ValidationError({
                "manager": "Um funcionário não pode ser gestor de si próprio."
            })

        if (
            self.hire_date and
            self.termination_date and
            self.termination_date < self.hire_date
        ):

            raise ValidationError({
                "termination_date":
                "A data de saída não pode ser inferior à data de admissão."
            })

    # ==========================================
    # HELPERS
    # ==========================================

    @property
    def is_active(self):

        return self.termination_date is None

    # ==========================================
    # META
    # ==========================================

    class Meta:

        unique_together = (
            'person',
            'branch'
        )

        indexes = [

            models.Index(fields=['code']),

            models.Index(fields=['hire_date']),

            models.Index(fields=['position']),

            models.Index(fields=['manager']),

            models.Index(fields=['person']),

        ]

    # ==========================================
    # RESAAS
    # ==========================================

    class RESAAS:

        label_field = "code person.full_name"

        searchable_fields = [

            "code",

            "person.name",

            "person.surname",

            "person.full_name"

        ]

        crud = True

        routes = {

            'list': "add_employee",

            'view': "view_employee",

            'add': "add_employee",

            'change': "change_employee"

        }

    # ==========================================
    # STRING REPRESENTATION
    # ==========================================

    def __str__(self):

        position = (
            self.position.label
            if self.position
            else "Sem Cargo"
        )

        return f"{self.person.full_name} ({position})"