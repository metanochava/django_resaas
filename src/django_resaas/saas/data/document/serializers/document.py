from rest_framework import serializers


from django_resaas.saas.models.document import Document
from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.data.document_type.serializers.document_type import DocumentTypeSerializer


def document_target_error(request, content_type, object_id):
    """Why a document cannot be attached to this object in the current
    context (None when it can): the object must exist and, when it belongs to
    a tenant (has an entity), to the current Entity - a document must never
    describe another tenant's record. A global object (a Person) is allowed:
    the document itself is the current Entity's (Document.entity)."""
    if content_type is None or object_id is None:
        return None
    Model = content_type.model_class()
    if Model is None:
        return "Unknown object type."
    manager = getattr(Model, "all_objects", Model._default_manager)
    target = manager.filter(pk=object_id).first()
    if target is None:
        return "Object not found."
    entity_id = getattr(target, "entity_id", None)
    if entity_id is not None and str(entity_id) != str(getattr(request, "entity_id", None)):
        return "Object not found."
    return None


def document_number_taken(entity_id, tipo_id, numero, exclude_pk=None):
    queryset = Document.all_objects.filter(entity_id=entity_id, tipo_id=tipo_id, numero=numero)
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()


class DocumentSerializer(BaseSerializer):
    # Read-only nested representation, same "xxx_data" convention as
    # EmployeeSerializer.position_data/job_grade_data - `tipo` on its
    # own only serializes as the DocumentType's raw id, not enough to
    # show a document ("ID Card - 123456") anywhere in the frontend.
    tipo_data = DocumentTypeSerializer(source='tipo', read_only=True)

    class Meta:
        model = Document
        fields = "__all__"
        # entity/branch come from the signed context, never from the body
        read_only_fields = ("entity", "branch")
        # (entity, tipo, numero) is checked in validate(): entity is not an
        # input, so DRF's automatic UniqueTogetherValidator cannot apply
        validators = []

    def validate(self, attrs):
        request = self.context.get("request")
        instance = self.instance

        content_type = attrs.get("content_type", getattr(instance, "content_type", None))
        object_id = attrs.get("object_id", getattr(instance, "object_id", None))
        error = document_target_error(request, content_type, object_id)
        if error:
            raise serializers.ValidationError({"object_id": [Translate.tdc(request, error)]})

        entity_id = getattr(instance, "entity_id", None) or getattr(request, "entity_id", None)
        tipo = attrs.get("tipo", getattr(instance, "tipo", None))
        numero = attrs.get("numero", getattr(instance, "numero", None))
        if tipo is not None and numero and document_number_taken(
            entity_id, getattr(tipo, "pk", tipo), numero, exclude_pk=getattr(instance, "pk", None)
        ):
            raise serializers.ValidationError({"numero": [Translate.tdc(request, "A document of this type with this number already exists.")]})

        return attrs
