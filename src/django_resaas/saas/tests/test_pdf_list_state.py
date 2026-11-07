"""The PDF list colours `state` like the frontend (utils/status.js):
Active positive, Inactive negative, other values their own tone."""
import pytest
from rest_framework.test import APIRequestFactory

from django_resaas.saas.core.utils.status_tone import status_tone
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("value, label, tone", [
    ("Active", None, "positive"),
    ("Inactive", None, "negative"),
    ("pending", None, "warning"),
    ("In progress", None, "warning"),
    ("scheduled", None, "info"),
    ("draft", None, "grey"),
    (1, "Ativo", "positive"),       # FrontEnd.state: an integer with its label
    (0, "Inactivo", "negative"),    # File.state
    ("something", None, "grey"),
])
def test_status_tone(value, label, tone):
    assert status_tone(value, label) == tone


def test_the_state_column_of_a_pdf_list_is_coloured(bootstrap_tenant):
    from django_resaas.saas.data.person.views.person import PersonAPIView

    tenant = bootstrap_tenant("pdf-list-state")
    Person.objects.create(name="Ana", surname="Active", gender="F", state="Active")
    Person.objects.create(name="Rui", surname="Inactive", gender="M", state="Inactive")
    request = APIRequestFactory().get("/")
    request.entity_id = tenant["entity"].id
    request.user = tenant["user"]
    view = PersonAPIView()
    view.request = request
    view.format_kwarg = None

    context = view.get_pdf_list_context(request, Person.objects.filter(surname__in=["Active", "Inactive"]).order_by("name"))
    column = [f["name"] for f in context["pdf_fields"]].index("state")
    cells = [str(row[column]) for row in context["pdf_rows"]]

    assert 'class="state state-positive"' in cells[0]
    assert 'class="state state-negative"' in cells[1]
