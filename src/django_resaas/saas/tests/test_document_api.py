"""DocumentAPIView/DocumentTypeAPIView used to be plain viewsets.ModelViewSet
(no BaseAPIView, no @registerView) - any authenticated user could create/
list Documents regardless of permissions, and document_path() would
AttributeError on `arquivo` upload (referenced entity_type/name, which
never existed on Document). Both are now BaseAPIView-based, permission-
checked, and document_path() uses fields the model actually has."""
import pytest

from django.contrib.contenttypes.models import ContentType

from django_resaas.saas.models.document import Document, DocumentType
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


def test_document_type_crud_works_for_a_permitted_role(bootstrap_tenant):
    tenant = bootstrap_tenant("document-type-crud")

    response = tenant["client"].post(
        "/api/django_resaas/documenttypes/",
        {"name": "Passport", "detalhes": "Travel document"},
        content_type="application/json",
    )

    assert response.status_code == 201, response.data
    assert response.data["name"] == "Passport"

    listed = tenant["client"].get("/api/django_resaas/documenttypes/")
    assert listed.status_code == 200, listed.data


def test_document_type_create_is_blocked_without_add_documenttype(bootstrap_tenant):
    """DocumentTypeAPIView was a plain viewsets.ModelViewSet before (no
    BaseAPIView) - any authenticated user could create one regardless of
    permissions. Confirms that gap is actually closed now."""
    tenant = bootstrap_tenant("document-type-no-perm")
    tenant["root_group"].permissions.remove(
        *tenant["root_group"].permissions.filter(codename="add_documenttype")
    )

    response = tenant["client"].post(
        "/api/django_resaas/documenttypes/",
        {"name": "Passport", "detalhes": "Travel document"},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert not DocumentType.objects.filter(name="Passport").exists()


def test_document_crud_and_generic_relation_to_person(bootstrap_tenant):
    tenant = bootstrap_tenant("document-crud")
    doc_type = DocumentType.objects.create(name="ID Card", detalhes="National ID")
    person = Person.objects.create(name="Lurdes", surname="Machado")

    response = tenant["client"].post(
        "/api/django_resaas/documents/",
        {
            "tipo": str(doc_type.id),
            "numero": "AB123456",
            "content_type": ContentType.objects.get_for_model(Person).id,
            "object_id": str(person.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 201, response.data

    document = Document.objects.get(id=response.data["id"])
    assert document.content_object == person
    assert response.data["tipo_data"]["name"] == "ID Card"


def test_document_path_uses_content_type_and_object_id_not_entity_type_and_name():
    """document_path() previously referenced instance.entity_type.name and
    instance.name - neither exists on Document, so any file upload would
    AttributeError. Confirms the fixed path builder only touches real
    fields."""
    from django_resaas.saas.models.document import document_path

    doc_type = DocumentType.objects.create(name="ID Card", detalhes="National ID")
    person = Person.objects.create(name="Nelson", surname="Utui")
    document = person.documents.create(tipo=doc_type, numero="999")

    path = document_path(document, "scan.pdf")

    assert path == f"documents/person/{person.id}/scan.pdf"
