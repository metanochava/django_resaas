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

    # The tenant that owns this record - set by the server from the signed
    # context (BaseAPIView.perform_create, Person.add_document, the person
    # registration service), never from the request body. It is what makes
    # BaseAPIView scope documents per Entity / Branch: a Person is global,
    # so the document cannot take its tenant from the object it describes.
    # Nullable only for rows that predate it and could not be attributed
    # (see migration 0004): nobody sees those (fail closed).
    entity = models.ForeignKey(
        "django_resaas.Entity", on_delete=models.CASCADE, null=True, blank=True,
        related_name="documents", editable=False,
    )
    branch = models.ForeignKey(
        "django_resaas.Branch", on_delete=models.CASCADE, null=True, blank=True,
        related_name="documents", editable=False,
    )

    class Meta:
        # a number is unique per type WITHIN an Entity: a global constraint
        # made the "already exists" error reveal another tenant's document
        constraints = [
            models.UniqueConstraint(fields=["entity", "tipo", "numero"], name="unique_document_number_per_entity"),
        ]
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