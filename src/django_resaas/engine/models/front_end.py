import uuid
from django.db import models


class FrontEnd(models.Model):

    name = models.CharField(max_length=100)
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

    state = models.IntegerField(
        default=1,
        choices=((0, 'Inactive'), (1, 'Ativo')),
    )

    class Meta:
        permissions = ()

    class RESAAS:
        label_field = "name"
        # route="view_entity"
        
    def __str__(self):
        return self.name
