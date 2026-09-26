"""GET .../<id>/pdf/ (BaseAPIView.pdf) for any model with no dedicated
template falls back to django_resaas/pdf/details.html - it used to point
at a non-existent detail.html and never fed the template the pdf_fields
it iterates over."""
import pytest

from django_resaas.saas.models.document import DocumentType
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


def test_pdf_of_an_object_with_no_dedicated_template_renders(bootstrap_tenant):
    tenant = bootstrap_tenant("pdf-details-person")
    person = Person.objects.create(
        name="Marta", surname="Sitoe", gender="F", email="marta@example.com"
    )

    response = tenant["client"].get(f"/api/django_resaas/persons/{person.id}/pdf/")

    assert response.status_code == 200, getattr(response, "data", response.content[:300])
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_pdf_fields_are_label_value_pairs_and_never_raw_objects(bootstrap_tenant):
    from django_resaas.saas.data.person.views.person import PersonAPIView
    from rest_framework.test import APIRequestFactory

    tenant = bootstrap_tenant("pdf-details-fields")
    person = Person.objects.create(
        name="Marta", surname="Sitoe", gender="F", date_of_birth="1990-05-20"
    )
    request = APIRequestFactory().get("/")
    request.entity_id = tenant["entity"].id
    person.refresh_from_db()
    view = PersonAPIView()
    view.request = request
    view.format_kwarg = None

    context = view.get_pdf_context(request, person)
    # labels go through Translate.tdc, which matches keys regardless of case
    # (like the frontend): compare them the same way
    fields = {f["label"].lower(): f["value"] for f in context["pdf_fields"]}

    assert fields["gender"] == "Feminine"
    assert fields["date of birth"] == "20/05/1990"
    assert fields["name"] == "Marta"
    assert "id" not in fields and "created at" not in fields
    assert all(isinstance(v, str) for v in fields.values())
