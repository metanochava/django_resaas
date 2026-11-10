"""App.description (a Text field): what the module is for, shown and edited
from the Modules page (list_app) through AppAPIView."""
import pytest

from django.db import models

from django_resaas.saas.models.app import App

pytestmark = pytest.mark.django_db


def test_the_description_is_a_text_field():
    assert isinstance(App._meta.get_field("description"), models.TextField)


def test_it_is_read_and_patched_through_the_api(bootstrap_tenant):
    client = bootstrap_tenant("app-description")["client"]
    app = App.objects.create(name="billing", state="Active")

    response = client.patch(f"/api/django_resaas/apps/{app.id}/",
                            {"description": "Invoices and payments"}, content_type="application/json")

    assert response.status_code == 200, response.data
    row = next(r for r in client.get("/api/django_resaas/apps/", {"page_size": 0}).data["results"]
               if r["name"] == "billing")
    assert row["description"] == "Invoices and payments"
