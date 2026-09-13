import uuid
from django.db import models
from django_resaas.saas.core.base.models import TimeModel


class File(TimeModel):

    # Entity required (every file belongs to exactly one tenant),
    # Branch optional (entity-wide uploads, e.g. an Entity's own Logo,
    # have no branch) - same tenant shape as NotificationRule/
    # NotificationSettings. Nullable at the DB level only for
    # already-existing rows this migration cannot safely attribute to
    # any tenant (File never recorded an owner before this) - every
    # new file should always set entity going forward.
    entity = models.ForeignKey(
        'django_resaas.Entity',
        on_delete=models.CASCADE,
        related_name='files',
        null=True,
        blank=True,
    )

    branch = models.ForeignKey(
        'django_resaas.Branch',
        on_delete=models.CASCADE,
        related_name='files',
        null=True,
        blank=True,
    )

    file = models.FileField(upload_to='files', null=True, blank=True)
    size = models.FloatField()
    model = models.CharField(max_length=100, null=True, help_text='Name do model que originou o file')

    state = models.IntegerField(default=1, null=True, choices=((0, 'Inactivo'), (1, 'Active')))

    ESCOLHA = (
        ('File', 'File'), ('Profile', 'Profile'), ('Logo', 'Logo'),
        ('Photo', 'Photo'), ('Cover', 'Cover'),
    )

    funcionalidade = models.CharField(max_length=100, null=True, default='File', choices=ESCOLHA)
    chamador = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        permissions = ()



    def __str__(self):
        return self.file.name if self.file else ''
