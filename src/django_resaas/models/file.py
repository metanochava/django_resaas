import uuid
from django.db import models
from django_resaas.core.base.models import TimeModel


class File(TimeModel):

    file = models.FileField(upload_to='files', null=True, blank=True)
    size = models.FloatField()
    model = models.CharField(max_length=100, null=True, help_text='Name do model que originou o file')

    estado = models.IntegerField(default=1, null=True, choices=((0, 'Inactivo'), (1, 'Activo')))

    ESCOLHA = (
        ('File', 'File'), ('Perfil', 'Perfil'), ('Logo', 'Logo'),
        ('Foto', 'Foto'), ('CapaSite', 'CapaSite'),
    )

    funcionalidade = models.CharField(max_length=100, null=True, default='File', choices=ESCOLHA)
    chamador = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        permissions = ()



    def __str__(self):
        return self.file.name if self.file else ''
