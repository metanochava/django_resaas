"""The language (header L) is not authorization: a request without it gets the
same permissions (a browser whose stored language had been emptied used to get
403 on every protected list and relation picker after a reload)."""
import pytest

pytestmark = pytest.mark.django_db


def test_lists_and_relations_answer_without_the_language_header(bootstrap_tenant):
    tenant = bootstrap_tenant("perm-no-lang")
    client = tenant["client"]
    context = client._credentials.get("HTTP_X_RESAAS_CONTEXT")
    assert context
    client.credentials(HTTP_X_RESAAS_CONTEXT=context)  # no HTTP_L

    listing = client.get("/api/django_resaas/persons/?page=1&page_size=5")
    picker = client.get("/api/django_resaas/relations/?model=django_resaas.Person&search=")

    assert listing.status_code == 200, listing.content[:200]
    assert picker.status_code == 200, picker.content[:200]
