"""person_matching_service (saas/core/services/) + PersonAPIView.match -
centralised Person duplicate-detection, reusable beyond add_employee
(future Patient/Student/Customer intake). Read-only: never creates,
merges or blocks anything itself."""
import pytest

from django_resaas.saas.core.services.person_matching_service import find_candidates
from django_resaas.saas.models.document import Document, DocumentType
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


def _grant_match_permission(root_group):
    from django.contrib.auth.models import Permission
    import django_resaas.saas.data.person.views.person  # noqa: F401 - populate VIEW_REGISTRY
    from django_resaas.saas.core.base.registry import VIEW_REGISTRY
    from django_resaas.saas.core.services.action_sync_service import ActionSyncService

    ActionSyncService.sync_registry(VIEW_REGISTRY)
    root_group.permissions.add(*Permission.objects.filter(codename="match_person"))


# =============================================================
# SERVICE - unit level
# =============================================================

def test_find_candidates_matches_by_email():
    Person.objects.create(name="Ana", surname="Costa", email="ana.costa@example.com")

    results = find_candidates({"email": "Ana.Costa@Example.com "})

    assert len(results) == 1
    assert results[0]["matched_fields"] == ["email"]


def test_find_candidates_matches_by_phone_despite_formatting_differences():
    Person.objects.create(name="Bruno", surname="Silva", phone="+258 84 123 4567")

    results = find_candidates({"phone": "0841234567"})

    assert len(results) == 1
    assert results[0]["matched_fields"] == ["phone"]


def test_find_candidates_matches_by_document_despite_formatting_differences():
    doc_type = DocumentType.objects.create(name="ID Card", detalhes="National ID")
    person = Person.objects.create(name="Carla", surname="Manjate")
    person.documents.create(tipo=doc_type, numero="123 456 789")

    results = find_candidates({"documents": [{"tipo": str(doc_type.id), "numero": "123456789"}]})

    assert len(results) == 1
    assert results[0]["person"].id == person.id
    assert results[0]["matched_fields"] == ["document"]


def test_find_candidates_requires_both_name_and_birth_date_together():
    Person.objects.create(name="Elsa", surname="Nhantumbo")

    # Name alone is deliberately NOT a match (CLAUDE.md: don't assume two
    # people are the same just because the names look similar).
    assert find_candidates({"name": "Elsa", "surname": "Nhantumbo"}) == []


def test_find_candidates_matches_by_name_and_birth_date_combo():
    Person.objects.create(
        name="Elsa", surname="Nhantumbo", date_of_birth="1990-05-01",
    )

    results = find_candidates({
        "name": "elsa", "surname": "NHANTUMBO", "date_of_birth": "1990-05-01",
    })

    assert len(results) == 1
    assert results[0]["matched_fields"] == ["name_and_birth_date"]


def test_find_candidates_ranks_document_match_above_weaker_signals():
    doc_type = DocumentType.objects.create(name="ID Card", detalhes="National ID")
    strong = Person.objects.create(name="Feliz", surname="Chissano", email="feliz@example.com")
    strong.documents.create(tipo=doc_type, numero="999")

    # Person.email is unique - a real second candidate needs a DIFFERENT
    # signal (phone) to legitimately co-match, not a duplicate email.
    weak = Person.objects.create(name="Outro", surname="Alguem", phone="841112222")

    results = find_candidates({
        "email": "feliz@example.com",
        "phone": "841112222",
        "documents": [{"tipo": str(doc_type.id), "numero": "999"}],
    })

    assert [r["person"].id for r in results] == [strong.id, weak.id]


def test_find_candidates_returns_empty_for_no_usable_signal():
    Person.objects.create(name="Sem", surname="Sinal")
    assert find_candidates({}) == []


# =============================================================
# API - PersonAPIView.match
# =============================================================

def test_match_endpoint_requires_permission(bootstrap_tenant):
    tenant = bootstrap_tenant("person-match-no-perm")

    response = tenant["client"].post(
        "/api/django_resaas/persons/match/", {"email": "x@example.com"},
        content_type="application/json",
    )

    # BaseAPIView.initial()'s own permission gate always responds via
    # ApiResponse.fail() (see saas/core/utils/api_response.py), whose
    # default status is 400, not 403 - matches the rest of the API's
    # existing convention for a denied action's own base permission.
    assert response.status_code == 400


def test_match_endpoint_returns_candidates_with_matched_fields_and_documents(bootstrap_tenant):
    tenant = bootstrap_tenant("person-match-ok")
    _grant_match_permission(tenant["root_group"])

    doc_type = DocumentType.objects.create(name="ID Card", detalhes="National ID")
    person = Person.objects.create(name="Graca", surname="Machel", email="graca@example.com")
    person.documents.create(tipo=doc_type, numero="777")

    response = tenant["client"].post(
        "/api/django_resaas/persons/match/",
        {"email": "graca@example.com", "documents": [{"tipo": str(doc_type.id), "numero": "777"}]},
        content_type="application/json",
    )

    assert response.status_code == 200, response.data
    results = response.data["results"]
    assert len(results) == 1
    assert results[0]["id"] == str(person.id)
    assert sorted(results[0]["matched_fields"]) == ["document", "email"]
    assert len(results[0]["documents"]) == 1
    assert results[0]["documents"][0]["numero"] == "777"


def test_match_endpoint_returns_empty_results_for_no_match(bootstrap_tenant):
    tenant = bootstrap_tenant("person-match-empty")
    _grant_match_permission(tenant["root_group"])

    response = tenant["client"].post(
        "/api/django_resaas/persons/match/",
        {"email": "nobody@example.com"},
        content_type="application/json",
    )

    assert response.status_code == 200, response.data
    assert response.data["results"] == []
