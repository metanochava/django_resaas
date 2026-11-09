"""Person.identity_document_type: the type of the person's identity document
(the person intake form fills the first document's type with it)."""
import pytest

from django_resaas.saas.models.document import DocumentType
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


def test_the_identity_document_type_is_saved_and_read(bootstrap_tenant):
    tenant = bootstrap_tenant("person-identity-type")
    bi = DocumentType.objects.create(name="BI", detalhes="Bilhete de Identidade")
    person = Person.objects.create(name="Rosa", surname="Chissano")

    response = tenant["client"].patch(
        f"/api/django_resaas/persons/{person.id}/", {"identity_document_type": str(bi.id)}, format="json",
    )

    assert response.status_code == 200, response.data
    assert Person.objects.get(pk=person.pk).identity_document_type_id == bi.id
    read = tenant["client"].get(f"/api/django_resaas/persons/{person.id}/").data["identity_document_type"]
    assert str(read.get("id") if isinstance(read, dict) else read) == str(bi.id)


def test_a_removed_type_leaves_the_person_without_one():
    bi = DocumentType.objects.create(name="BI", detalhes="x")
    person = Person.objects.create(name="Ana", surname="Bila", identity_document_type=bi)

    bi.hard_delete() if hasattr(bi, "hard_delete") else DocumentType.all_objects.filter(pk=bi.pk).hard_delete()

    assert Person.objects.get(pk=person.pk).identity_document_type_id is None


def test_people_registered_before_get_their_first_documents_type(bootstrap_tenant):
    """Migration 0017: the type of the first document (one with a number
    first) for people without one; nothing for people without documents."""
    import importlib

    from django.apps import apps
    from django.contrib.contenttypes.models import ContentType

    from django_resaas.saas.models.document import Document

    fill = importlib.import_module(
        "django_resaas.saas.migrations.0017_fill_person_identity_document_type"
    ).fill_identity_document_type
    tenant = bootstrap_tenant("person-identity-fill")
    bi = DocumentType.objects.create(name="BI", detalhes="x")
    passport = DocumentType.objects.create(name="Passaporte", detalhes="x")
    with_docs = Person.objects.create(name="Rosa", surname="Chissano")
    without = Person.objects.create(name="Ana", surname="Bila")
    already = Person.objects.create(name="Eva", surname="Mondlane", identity_document_type=passport)
    for person, tipo, numero in ((with_docs, passport, ""), (with_docs, bi, "110100253481B"), (already, bi, "2")):
        Document.objects.create(tipo=tipo, numero=numero, content_type=ContentType.objects.get_for_model(Person),
                                object_id=person.id, entity=tenant["entity"], branch=tenant["branch"])

    fill(apps, None)
    fill(apps, None)  # idempotent

    assert Person.objects.get(pk=with_docs.pk).identity_document_type_id == bi.id
    assert Person.objects.get(pk=without.pk).identity_document_type_id is None
    assert Person.objects.get(pk=already.pk).identity_document_type_id == passport.id
