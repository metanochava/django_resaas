"""An empty photo on PATCH must never delete the Person's current photo -
shared by every flow that edits a Person (employee, patient, ...)."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db

def _png_bytes():
    import io
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


PNG = _png_bytes()


def _person_with_photo():
    person = Person.objects.create(name="Foto", surname="Existente")
    person.photo = SimpleUploadedFile("keep.png", PNG, content_type="image/png")
    person.save()
    return person


def test_patch_with_null_photo_keeps_the_existing_photo(bootstrap_tenant):
    tenant = bootstrap_tenant("person-photo-null")
    person = _person_with_photo()
    original = person.photo.name

    response = tenant["client"].patch(
        f"/api/django_resaas/persons/{person.id}/",
        {"name": "Foto", "photo": None},
        format="json",
    )

    assert response.status_code == 200, response.data
    person.refresh_from_db()
    assert person.photo.name == original


def test_patch_with_empty_string_photo_keeps_the_existing_photo(bootstrap_tenant):
    tenant = bootstrap_tenant("person-photo-empty")
    person = _person_with_photo()
    original = person.photo.name

    response = tenant["client"].patch(
        f"/api/django_resaas/persons/{person.id}/",
        {"name": "Foto", "photo": ""},
        format="multipart",
    )

    assert response.status_code == 200, response.data
    person.refresh_from_db()
    assert person.photo.name == original


def test_patch_without_photo_key_keeps_the_existing_photo(bootstrap_tenant):
    tenant = bootstrap_tenant("person-photo-absent")
    person = _person_with_photo()
    original = person.photo.name

    tenant["client"].patch(f"/api/django_resaas/persons/{person.id}/", {"surname": "Novo"}, format="json")

    person.refresh_from_db()
    assert person.photo.name == original
    assert person.surname == "Novo"


def test_patch_with_a_new_photo_replaces_it(bootstrap_tenant):
    tenant = bootstrap_tenant("person-photo-new")
    person = _person_with_photo()
    original = person.photo.name

    response = tenant["client"].patch(
        f"/api/django_resaas/persons/{person.id}/",
        {"photo": SimpleUploadedFile("new.png", PNG, content_type="image/png")},
        format="multipart",
    )

    assert response.status_code == 200, response.data
    person.refresh_from_db()
    assert person.photo.name != original
    assert "new" in person.photo.name
