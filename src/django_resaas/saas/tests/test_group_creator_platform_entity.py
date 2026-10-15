"""group_creator(): the profiles are linked to the platform Entity - the
oldest Entity of the SaaS EntityType - found by its type, never by a
hard-coded name; on a new installation without it they are still created
(and linked to the type), and no Entity is ever created here."""
import pytest

from django_resaas.saas.core.utils.group_creator import group_creator
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity_type_group import EntityTypeGroup

pytestmark = pytest.mark.django_db


@pytest.fixture
def saas_type():
    entity_type, _ = EntityType.objects.get_or_create(name="SaaS", defaults={"state": "Active"})
    Entity.objects.filter(entity_type=entity_type).delete()
    return entity_type


def test_without_a_platform_entity_the_profiles_are_still_created(saas_type):
    report = group_creator(["Platform Less"])

    assert report["groups_created"] == ["Platform Less"]
    assert EntityTypeGroup.objects.filter(entity_type=saas_type, group__name="Platform Less").exists()
    assert not EntityGroup.objects.filter(group__name="Platform Less").exists()
    assert not Entity.objects.filter(entity_type=saas_type).exists()   # nothing invented


def test_the_profiles_go_to_the_oldest_entity_of_the_saas_type(saas_type):
    first = Entity.objects.create(name="Platform", entity_type=saas_type)
    Entity.objects.create(name="Second", entity_type=saas_type)

    group_creator(["Platform Linked"])
    group_creator(["Platform Linked"])   # idempotent

    links = EntityGroup.objects.filter(group__name="Platform Linked")
    assert list(links.values_list("entity_id", flat=True)) == [first.id]
