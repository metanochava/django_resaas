"""
Phase 3 of the Patient-longitudinal/Health/Pharmacy initiative (see
back/docs/architecture/patient-longitudinal-health-pharmacy.md):
Person.photo - a single identification photo shared by Employee and
Patient without duplicating it per persona, mirroring the existing
User.profile ImageField pattern already used in this codebase.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from django_resaas.engine.data.person.serializers.person import PersonSerializer
from django_resaas.engine.models.person import Person

pytestmark = pytest.mark.django_db


def test_photo_field_is_optional():
    field = Person._meta.get_field("photo")
    assert field.blank is True
    assert field.null is True


def test_person_can_be_created_without_a_photo():
    person = Person.objects.create(name="Joao", surname="Alberto")
    assert not person.photo


def test_person_can_be_saved_with_a_photo(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path

    photo = SimpleUploadedFile(
        "photo.jpg", b"fake-image-bytes", content_type="image/jpeg"
    )
    person = Person.objects.create(name="Maria", surname="Fernandes", photo=photo)

    assert person.photo
    assert "images/persons/" in person.photo.name


def test_serializer_exposes_photo_field(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path

    person = Person.objects.create(name="Carlos", surname="Nunes")
    assert "photo" in PersonSerializer(person).data
