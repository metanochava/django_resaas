from django.db import models
from django_resaas.core.base.models import BaseModel

class Employee(BaseModel):
    person = models.ForeignKey(
        'django_resaas.Person',
        on_delete=models.CASCADE,
        related_name='employees'
    )

    codigo = models.CharField(max_length=50)
    cargo = models.CharField(max_length=100)

    data_admissao = models.DateField()
    data_saida = models.DateField(null=True, blank=True)

    ativo = models.BooleanField(default=True)

    gestor = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subordinados'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['person', 'branch'],
                name='unique_person_branch'
            )
        ]

    def __str__(self):
        return f"{self.person.name_completo} ({self.cargo})"