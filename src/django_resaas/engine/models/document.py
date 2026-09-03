import uuid
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django_resaas.engine.core.base.models import TimeModel


def document_path(instance, file_name):
    return f'{instance.entity_type.name}/{instance.name}/{file_name}'

class DocumentType(TimeModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    detalhes = models.CharField(max_length=200)
    class RESAAS:
        label_field = "name"
        crud = True
        routes={
            'list': "add_documenttype",
            'view': "view_documenttype",
            'add': "add_documenttype",
            'change': "change_documenttype"
        }

    def __str__(self):
        return self.name

class Document(TimeModel):
    tipo = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    numero = models.CharField(max_length=100)

    data_emissao = models.DateField(null=True, blank=True)
    data_validade = models.DateField(null=True, blank=True)

    arquivo = models.FileField(upload_to=document_path, null=True, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = ('tipo', 'numero')
    class RESAAS:
        label_field = "numero"
        crud = True
        routes={
            'list': "add_document",
            'view': "view_document",
            'add': "add_document",
            'change': "change_document"
        }
    def __str__(self):
        return f"{self.tipo.name} - {self.numero}"