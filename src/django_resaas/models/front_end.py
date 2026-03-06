import uuid
from django.db import models


class FrontEnd(models.Model):

    nome = models.CharField(max_length=100)
    fek = models.CharField(max_length=255, unique=True)
    fep = models.CharField(max_length=255)

    access = models.CharField(
        max_length=20,
        choices=(
            ('read', 'Read'),
            ('write', 'Write'),
            ('readwrite', 'Read & Write'),
            ('super', 'Super'),
        ),
        default='read',
    )

    estado = models.IntegerField(
        default=1,
        choices=((0, 'Inativo'), (1, 'Ativo')),
    )

    class Meta:
        permissions = ()

    def __str__(self):
        return self.nome
