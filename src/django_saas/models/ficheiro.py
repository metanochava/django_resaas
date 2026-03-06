import uuid
from django.db import models
from django_saas.core.base.models import TimeModel


class Ficheiro(TimeModel):

    ficheiro = models.FileField(upload_to='ficheiros', null=True, blank=True)
    size = models.FloatField()
    modelo = models.CharField(max_length=100, null=True, help_text='Nome do modelo que originou o ficheiro')

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
        return self.ficheiro.name if self.ficheiro else ''
