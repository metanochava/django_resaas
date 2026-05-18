from django.db import models
from django_resaas.core.base.models import BaseModel


class JobPosition(BaseModel):
    title = models.CharField(max_length=150)
    code = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    department = models.ForeignKey(
        'hr.Department',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='positions'
    )

    class Meta:
        ordering = ['title']
        unique_together = ('entity', 'title')

    def __str__(self):
        return self.title