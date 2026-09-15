"""Same bug class as test_entity_apps_models_scope.py's addApp/addModel
fix: any get_or_create()/create() on a TimeModel subclass (state
defaults to "Inactive" - see core/base/models.py) that omits `state=`,
or passes it as a bare kwarg instead of inside `defaults=`, silently
creates an inactive row (bare kwarg also pollutes the get_or_create()
lookup filter, risking a duplicate row if one already exists inactive).

Covers the "Add" flows the user reported as still broken after the
Entity/EntityType apps/models fix: EntityAPIView.createGroup/addGroup,
EntityTypeAPIView.createGroup/addGroup (both cascading to EntityGroup/
BranchGroup), and the generic BranchUserGroupAPIView (plain
ModelViewSet - the "Branch user groups" CRUD screen never sends
`state`, so it fell back to the model default)."""
import pytest

from django_resaas.saas.models.branch_group import BranchGroup
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_type_group import EntityTypeGroup
from django_resaas.saas.models.group import Group

pytestmark = pytest.mark.django_db


class TestEntityCreateAddGroupState:
    def test_create_group_activates_entity_and_branch_group(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-creategroup-state")
        entity, client = tenant["entity"], tenant["client"]

        response = client.post(
            f"/api/django_resaas/entitys/{entity.id}/createGroup/",
            {"name": "Clinical Operations Supervisor"},
        )

        assert response.status_code == 200
        group_id = response.json()["id"]

        entity_group = EntityGroup.objects.get(entity=entity, group_id=group_id)
        assert entity_group.state == "Active"

        branch_group = BranchGroup.objects.get(branch=tenant["branch"], group_id=group_id)
        assert branch_group.state == "Active"

    def test_add_group_activates_entity_and_branch_group(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addgroup-state")
        entity, client = tenant["entity"], tenant["client"]
        group = Group.objects.create(name="Billing Clerk")

        response = client.post(
            f"/api/django_resaas/entitys/{entity.id}/addGroup/",
            {"group": group.id},
        )

        assert response.status_code == 200
        entity_group = EntityGroup.objects.get(entity=entity, group=group)
        assert entity_group.state == "Active"

        branch_group = BranchGroup.objects.get(branch=tenant["branch"], group=group)
        assert branch_group.state == "Active"


class TestEntityTypeCreateAddGroupState:
    def test_create_group_activates_entity_type_and_cascades_to_entity(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entitytype-creategroup-state")
        entity, client = tenant["entity"], tenant["client"]
        entity_type_id = entity.entity_type_id

        response = client.post(
            f"/api/django_resaas/entitytypes/{entity_type_id}/createGroup/",
            {"name": "Ward Supervisor"},
        )

        assert response.status_code == 200
        group_id = response.json()["id"]

        et_group = EntityTypeGroup.objects.get(entity_type_id=entity_type_id, group_id=group_id)
        assert et_group.state == "Active"

        entity_group = EntityGroup.objects.get(entity=entity, group_id=group_id)
        assert entity_group.state == "Active"

    def test_add_group_activates_entity_type_group(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entitytype-addgroup-state")
        entity, client = tenant["entity"], tenant["client"]
        entity_type_id = entity.entity_type_id
        group = Group.objects.create(name="Triage Nurse")

        response = client.post(
            f"/api/django_resaas/entitytypes/{entity_type_id}/addGroup/",
            {"group": group.id},
        )

        assert response.status_code == 200
        et_group = EntityTypeGroup.objects.get(entity_type_id=entity_type_id, group=group)
        assert et_group.state == "Active"


class TestBranchUserGroupGenericCreateState:
    def test_generic_add_defaults_state_to_active(self, bootstrap_tenant):
        tenant = bootstrap_tenant("branchusergroup-state")
        branch, client = tenant["branch"], tenant["client"]
        user, group = tenant["user"], tenant["root_group"]

        # o próprio bootstrap já criou este par - usa um Group novo para
        # exercitar mesmo caminho de create() que a tela de Add genérica
        other_group = Group.objects.create(name="Auditor")

        response = client.post(
            "/api/django_resaas/branchusergroups/",
            {"user": user.id, "branch": branch.id, "group": other_group.id},
        )

        assert response.status_code == 201
        bug = BranchUserGroup.objects.get(user=user, branch=branch, group=other_group)
        assert bug.state == "Active"
