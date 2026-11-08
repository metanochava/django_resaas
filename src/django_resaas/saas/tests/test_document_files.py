"""A Document may have several files (DocumentFile): POST
documents/{id}/files/ adds them, DELETE documents/{id}/files/{file_id}/
removes one, both with change_document and only on this tenant's document;
PersonAPIView.add_document and the registration accept several files too."""
import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from django_resaas.saas.models.document import Document, DocumentFile, DocumentType
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db
URL = "/api/django_resaas/documents/"


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _file(name="frente.png"):
    return SimpleUploadedFile(name, b"\x89PNG fake", content_type="image/png")


def _document(tenant, numero="BI-1"):
    person = Person.objects.create(name="Lurdes", surname="Machado")
    return Document.objects.create(
        tipo=DocumentType.objects.get_or_create(name="BI", defaults={"detalhes": "x"})[0], numero=numero,
        content_type=ContentType.objects.get_for_model(Person), object_id=person.id,
        entity=tenant["entity"], branch=tenant["branch"],
    )


def test_several_files_are_added_and_listed(bootstrap_tenant):
    tenant = bootstrap_tenant("doc-files-add")
    document = _document(tenant)

    response = tenant["client"].post(
        f"{URL}{document.id}/files/", {"files": [_file("frente.png"), _file("verso.png")]}, format="multipart",
    )

    assert response.status_code == 201, response.data
    assert sorted(f["name"] for f in response.data["files"]) == ["frente.png", "verso.png"]
    detail = tenant["client"].get(f"{URL}{document.id}/").data
    assert len(detail["files"]) == 2


def test_no_file_is_a_400(bootstrap_tenant):
    tenant = bootstrap_tenant("doc-files-none")
    document = _document(tenant)

    response = tenant["client"].post(f"{URL}{document.id}/files/", {}, format="multipart")

    assert response.status_code == 400


def test_one_file_is_removed(bootstrap_tenant):
    tenant = bootstrap_tenant("doc-files-remove")
    document = _document(tenant)
    tenant["client"].post(f"{URL}{document.id}/files/", {"files": [_file("a.png"), _file("b.png")]}, format="multipart")
    first = document.files.order_by("name").first()

    response = tenant["client"].delete(f"{URL}{document.id}/files/{first.id}/")

    assert response.status_code == 204
    assert [f.name for f in Document.objects.get(pk=document.pk).files.all()] == ["b.png"]


def test_another_entity_cannot_add_or_remove_files(bootstrap_tenant):
    a, b = bootstrap_tenant("doc-files-a"), bootstrap_tenant("doc-files-b")
    b["client"].raise_request_exception = False
    document = _document(a)
    a["client"].post(f"{URL}{document.id}/files/", {"files": [_file()]}, format="multipart")
    row = document.files.first()

    added = b["client"].post(f"{URL}{document.id}/files/", {"files": [_file()]}, format="multipart")
    removed = b["client"].delete(f"{URL}{document.id}/files/{row.id}/")

    assert added.status_code == 404
    assert removed.status_code == 404
    assert DocumentFile.objects.filter(document=document).count() == 1


def test_add_document_takes_several_files(bootstrap_tenant):
    from django.contrib.auth.models import Permission
    from django_resaas.saas.tests.test_person_add_document import _sync_saas_actions

    tenant = bootstrap_tenant("doc-files-person")
    _sync_saas_actions()
    tenant["root_group"].permissions.add(*Permission.objects.filter(codename="add_document_person"))
    doc_type = DocumentType.objects.create(name="Passport", detalhes="x")
    person = Person.objects.create(name="Rosa", surname="Chissano")

    response = tenant["client"].post(
        f"/api/django_resaas/persons/{person.id}/add_document/",
        {"tipo": str(doc_type.id), "numero": "P-77", "files": [_file("p1.png"), _file("p2.png")]},
        format="multipart",
    )

    assert response.status_code == 201, response.data
    assert len(response.data["files"]) == 2


def test_the_older_single_file_still_works(bootstrap_tenant):
    from django.contrib.auth.models import Permission
    from django_resaas.saas.tests.test_person_add_document import _sync_saas_actions

    tenant = bootstrap_tenant("doc-files-legacy")
    _sync_saas_actions()
    tenant["root_group"].permissions.add(*Permission.objects.filter(codename="add_document_person"))
    doc_type = DocumentType.objects.create(name="NUIT", detalhes="x")
    person = Person.objects.create(name="Ana", surname="Bila")

    response = tenant["client"].post(
        f"/api/django_resaas/persons/{person.id}/add_document/",
        {"tipo": str(doc_type.id), "numero": "N-1", "arquivo": _file("old.png")},
        format="multipart",
    )

    assert response.status_code == 201, response.data
    assert [f["name"] for f in response.data["files"]] == ["old.png"]


def test_registration_documents_carry_their_files():
    from types import SimpleNamespace
    from django_resaas.saas.core.services.person_registration_service import documents_with_files

    f1, f2, f3 = _file("a.png"), _file("b.png"), _file("c.png")
    request = SimpleNamespace(FILES={"k1": f1, "k2": f2, "old": f3})

    docs = documents_with_files(request, [
        {"tipo": "t", "numero": "1", "_file_keys": ["k1", "k2"]},
        {"tipo": "t", "numero": "2", "_file_key": "old"},
        {"tipo": "t", "numero": "3"},
    ])

    assert [len(d["arquivos"]) for d in docs] == [2, 1, 0]
    assert "_file_keys" not in docs[0]
