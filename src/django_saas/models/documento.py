import uuid
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django_saas.core.base.models import TimeModel


def documento_path(instance, file_name):
    return f'{instance.tipo_entidade.nome}/{instance.nome}/{file_name}'

class TipoDocumento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=200)
    detalhes = models.CharField(max_length=200)

    def __str__(self):
        return self.nome

class Documento(TimeModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tipo = models.ForeignKey(TipoDocumento, on_delete=models.CASCADE)
    numero = models.CharField(max_length=100)

    data_emissao = models.DateField(null=True, blank=True)
    data_validade = models.DateField(null=True, blank=True)

    arquivo = models.FileField(upload_to=documento_path, null=True, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = ('tipo', 'numero')

    def __str__(self):
        return f"{self.tipo.nome} - {self.numero}"