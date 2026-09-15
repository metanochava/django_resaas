"""group_creator() (saas/core/utils/group_creator.py) - called from
saude/sales/inventory/farmacia's AppConfig.ready() - used to bootstrap
its own "SaaS"/"Tenant" EntityType/Entity with `state='Active'` as a bare
get_or_create() kwarg instead of inside `defaults=`. Since `state` is a
CharField (TimeModel.state, choices "Inactive"/"Active"), `state='Active'`
became part of the lookup filter too, so it could never find the
"SaaS"/"Tenant" row already created with state="Active" by
create_root/BootstrapService/bootstrap.py/app_service.py - producing a
second, divergent EntityType/Entity row (state="1") every time a
business module bootstraps alongside one of those commands, exactly as
reported live."""
import pytest

from django_resaas.saas.core.utils.group_creator import group_creator
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_type import EntityType

pytestmark = pytest.mark.django_db


def test_group_creator_reuses_existing_active_saas_entity_type():
    existing = EntityType.objects.create(name="SaaS", state="Active")

    group_creator(groups=["Guest"])

    assert EntityType.objects.filter(name="SaaS").count() == 1
    existing.refresh_from_db()
    assert existing.state == "Active"


def test_group_creator_reuses_existing_active_tenant_entity():
    entity_type = EntityType.objects.create(name="SaaS", state="Active")
    existing = Entity.objects.create(
        name="Tenant", entity_type=entity_type, state="Active"
    )

    group_creator(groups=["Guest"])

    assert Entity.objects.filter(name="Tenant").count() == 1
    existing.refresh_from_db()
    assert existing.state == "Active"


def test_group_creator_creates_active_saas_entity_type_when_missing():
    group_creator(groups=["Guest"])

    entity_type = EntityType.objects.get(name="SaaS")
    assert entity_type.state == "Active"

    entity = Entity.objects.get(name="Tenant")
    assert entity.state == "Active"
