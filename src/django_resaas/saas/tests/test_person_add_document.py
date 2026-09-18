"""PersonAPIView.add_document - attaches one new Document to an EXISTING
Person (person.documents.create(...), the same generic-relation call
employee_registration_service already uses for a brand new Person).
Added for change_employee's edit flow (EmployeeSEPage.vue), which -
unlike add_employee's atomic register() - edits a Person that already
exists, so a document added mid-edit can't ride inside that one-shot
creation action."""
import pytest

from django_resaas.saas.models.document import Document, DocumentType
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


def _sync_saas_actions():
    import django_resaas.saas.data.person.views.person  # noqa: F401 - populate VIEW_REGISTRY
    from django_resaas.saas.core.base.registry import VIEW_REGISTRY
    from django_resaas.saas.core.services.action_sync_service import ActionSyncService

    ActionSyncService.sync_registry(VIEW_REGISTRY)


def _grant_add_document_action(root_group):
    from django.contrib.auth.models import Permission

    _sync_saas_actions()
    root_group.permissions.add(*Permission.objects.filter(codename="add_document_person"))


def _bootstrap(bootstrap_tenant, username):
    tenant = bootstrap_tenant(username)
    _grant_add_document_action(tenant["root_group"])
    return tenant


def test_add_document_attaches_a_new_document_to_an_existing_person(bootstrap_tenant):
    tenant = _bootstrap(bootstrap_tenant, "person-add-document")
    doc_type = DocumentType.objects.create(name="ID Card", detalhes="National ID")
    person = Person.objects.create(name="Rosa", surname="Chissano")

    response = tenant["client"].post(
        f"/api/django_resaas/persons/{person.id}/add_document/",
        {"tipo": str(doc_type.id), "numero": "555666777"},
        format="multipart",
    )

    assert response.status_code == 201, response.data
    document = Document.objects.get(numero="555666777")
    assert document.content_object == person


def test_add_document_requires_tipo_and_numero(bootstrap_tenant):
    tenant = _bootstrap(bootstrap_tenant, "person-add-document-missing")
    person = Person.objects.create(name="Alfredo", surname="Nhaca")

    response = tenant["client"].post(
        f"/api/django_resaas/persons/{person.id}/add_document/",
        {"numero": "999"},
        format="multipart",
    )

    assert response.status_code == 400


def test_add_document_is_blocked_without_the_reused_add_document_permission(bootstrap_tenant):
    """add_document_person (this action's own base gate) is granted, but
    the real, reused add_document permission is not - mirrors
    EmployeeAPIView.register()'s own double permission-check pattern."""
    tenant = _bootstrap(bootstrap_tenant, "person-add-document-no-perm")
    tenant["root_group"].permissions.remove(
        *tenant["root_group"].permissions.filter(codename="add_document")
    )
    doc_type = DocumentType.objects.create(name="ID Card", detalhes="National ID")
    person = Person.objects.create(name="Celia", surname="Massingue")

    response = tenant["client"].post(
        f"/api/django_resaas/persons/{person.id}/add_document/",
        {"tipo": str(doc_type.id), "numero": "111"},
        format="multipart",
    )

    assert response.status_code == 403
    assert not Document.objects.filter(numero="111").exists()


def test_add_document_rejects_an_unknown_document_type(bootstrap_tenant):
    tenant = _bootstrap(bootstrap_tenant, "person-add-document-bad-type")
    person = Person.objects.create(name="Julio", surname="Fumo")

    response = tenant["client"].post(
        f"/api/django_resaas/persons/{person.id}/add_document/",
        {"tipo": "00000000-0000-0000-0000-000000000000", "numero": "222"},
        format="multipart",
    )

    assert response.status_code == 400
