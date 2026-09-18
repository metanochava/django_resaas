import uuid
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django_resaas.saas.core.base.models import TimeModel


def document_path(instance, file_name):
    # Document has no `entity_type`/`name` (it never did - this
    # referenced attributes that don't exist on the model, so any
    # upload would AttributeError). object_id is stable the moment the
    # row exists (set together with content_type by the GenericRelation
    # manager - see Person.documents), content_type.model gives a
    # human-readable folder per owning model (person, employee, ...).
    return f'documents/{instance.content_type.model}/{instance.object_id}/{file_name}'

class DocumentType(TimeModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    detalhes = models.CharField(max_length=200)
    class RESAAS:
        label_field = "name"
        crud = True
        routes={
            'list': "list_documenttype",
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
            'list': "list_document",
            'view': "view_document",
            'add': "add_document",
            'change': "change_document"
        }
    def __str__(self):
        return f"{self.tipo.name} - {self.numero}"