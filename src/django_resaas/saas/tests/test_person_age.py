"""
Person.age is a @property (see models/person.py) - PersonSerializer.
get_age() used to call it as a method (obj.age()), which would crash
serializing ANY Person the moment obj.age resolves to a plain int/None
(TypeError: 'int'/'NoneType' object is not callable).
"""
import pytest
from datetime import date

from django_resaas.saas.data.person.serializers.person import PersonSerializer
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


def test_serializer_exposes_age_for_a_person_with_date_of_birth():
    person = Person.objects.create(
        name="Joao", surname="Alberto", date_of_birth=date(1990, 1, 1),
    )

    data = PersonSerializer(person).data

    assert isinstance(data["age"], int)
    assert data["age"] == person.age


def test_serializer_exposes_none_age_without_a_date_of_birth():
    person = Person.objects.create(name="Maria", surname="Fernandes")

    data = PersonSerializer(person).data

    assert data["age"] is None
