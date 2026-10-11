"""Documents belong to the Entity / Branch of the signed context (Document.entity):
BaseAPIView scopes them, numbers are unique per Entity, a document cannot be
attached to another tenant's object, and Person endpoints only show / create
the current Entity's documents."""
import pytest
from django.contrib.contenttypes.models import ContentType

from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.document import Document, DocumentType
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db
URL = "/api/django_resaas/documents/"


def _post(client, doc_type, target, numero="AB1", **extra):
    return client.post(URL, {
        "tipo": str(doc_type.id), "numero": numero,
        "content_type": ContentType.objects.get_for_model(type(target)).id, "object_id": str(target.id), **extra,
    }, format="json")


@pytest.fixture
def two(bootstrap_tenant):
    a, b = bootstrap_tenant("doc-iso-a"), bootstrap_tenant("doc-iso-b")
    for t in (a, b):
        t["client"].raise_request_exception = False
    return a, b, DocumentType.objects.create(name="ID Card", detalhes="x"), Person.objects.create(name="Lurdes", surname="Machado")


def test_a_document_takes_the_tenant_from_the_context_not_the_body(two):
    a, b, doc_type, person = two
    response = _post(a["client"], doc_type, person, entity=str(b["entity"].id), branch=str(b["branch"].id))
    assert response.status_code == 201, response.content
    doc = Document.objects.get(pk=response.json()["id"])
    assert (doc.entity_id, doc.branch_id) == (a["entity"].id, a["branch"].id)


def test_another_entity_never_sees_or_changes_the_document(two):
    a, b, doc_type, person = two
    doc_id = _post(a["client"], doc_type, person).json()["id"]
    listed = b["client"].get(URL).json()
    rows = listed["results"] if isinstance(listed, dict) else listed
    assert doc_id not in [r["id"] for r in rows]
    assert b["client"].get(f"{URL}{doc_id}/").status_code == 404
    assert b["client"].patch(f"{URL}{doc_id}/", {"numero": "X"}, format="json").status_code == 404
    assert b["client"].delete(f"{URL}{doc_id}/").status_code == 404
    assert Document.objects.get(pk=doc_id).numero == "AB1"


def test_numbers_are_unique_per_entity_only(two):
    a, b, doc_type, person = two
    assert _post(a["client"], doc_type, person).status_code == 201
    assert _post(b["client"], doc_type, person).status_code == 201
    duplicate = _post(a["client"], doc_type, person)
    assert duplicate.status_code == 400
    assert "numero" in duplicate.json()["error"]["details"]


def test_a_document_cannot_describe_another_tenants_object(two):
    a, b, doc_type, _ = two
    response = _post(a["client"], doc_type, Branch.objects.get(pk=b["branch"].id))
    assert response.status_code == 400
    assert "object_id" in response.json()["error"]["details"]


def test_person_endpoints_only_use_the_current_entitys_documents(two):
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType as CT

    a, b, doc_type, person = two
    # an @resaas_action permission is granted on purpose, not by default
    action_perm, _ = Permission.objects.get_or_create(
        codename="add_document_person", content_type=CT.objects.get_for_model(Person),
        defaults={"name": "Can add document person"},
    )
    b["root_group"].permissions.add(action_perm)
    created = b["client"].post(f"/api/django_resaas/persons/{person.id}/add_document/",
                               {"tipo": str(doc_type.id), "numero": "B-1"}, format="json")
    assert created.status_code == 201, created.content
    assert Document.objects.get(numero="B-1").entity_id == b["entity"].id
    _post(a["client"], doc_type, person, numero="A-1")
    match = a["client"].post("/api/django_resaas/persons/match/", {"name": "Lurdes", "surname": "Machado"}, format="json").json()
    numbers = {d["numero"] for row in match.get("results", []) for d in row["documents"]}
    assert "B-1" not in numbers
