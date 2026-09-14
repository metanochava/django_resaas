"""
Branch.photo/description - shown on the location card (Google Maps
InfoWindow) in AddressLocationPicker.vue, and reusable anywhere else a
Branch needs a thumbnail/summary. Plain concrete fields on Branch, so
BranchSerializer's existing fields="__all__" + BaseSerializer's
FileFieldsMixin already handle them the same way Person.photo already
works - this only locks that in as a regression test.
"""
import io

import pytest
from PIL import Image
from rest_framework.test import APIClient

from django_resaas.saas.models.branch import Branch

pytestmark = pytest.mark.django_db


def _make_test_image():
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
    buffer.seek(0)
    buffer.name = "branch.png"
    return buffer


def test_branch_description_and_photo_round_trip(bootstrap_tenant):
    tenant = bootstrap_tenant("map-card")
    branch = Branch.objects.create(name="Map Card Branch", entity=tenant["entity"])

    response = tenant["client"].patch(
        f"/api/django_resaas/branchs/{branch.id}/",
        {"description": "Our flagship location.", "photo": _make_test_image()},
        format="multipart",
    )

    assert response.status_code == 200, response.data
    assert response.data["description"] == "Our flagship location."
    assert response.data["photo"]

    branch.refresh_from_db()
    assert branch.description == "Our flagship location."
    assert branch.photo.name
