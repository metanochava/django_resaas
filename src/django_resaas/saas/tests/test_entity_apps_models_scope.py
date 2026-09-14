"""EntityAPIView.addApp/removeApp (new) and addModel (now validated) -
an Entity may only activate an App/Model that its own EntityType
already has (EntityTypeApp/EntityTypeModel) - the EntityType defines
the available universe, the Entity just picks within it. Mirrors the
already-existing EntityTypeAPIView.addApp/addModel validation-free
"EntityType picks from the global App/ContentType registry" level,
one level down.

apps/models/addApp/removeApp/addModel/removeModel are each their own
@resaas_action with a dedicated permission (`{action}_entity`) - one
permission per capability, never one shared across several actions
(see EntityAPIView in views/entity.py). Enforced directly via
@hasPermission since EntityAPIView is a plain ModelViewSet, not
BaseAPIView (whose initial() would otherwise read the same
@resaas_action metadata automatically)."""
import pytest
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from django_resaas.saas.core.tenant.context import ResaasContextService
from django_resaas.saas.models.app import App
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_app import EntityApp
from django_resaas.saas.models.entity_model import EntityModel
from django_resaas.saas.models.entity_type_app import EntityTypeApp
from django_resaas.saas.models.entity_type_model import EntityTypeModel
from django_resaas.saas.models.group import Group

pytestmark = pytest.mark.django_db

ENTITY_ACTION_CODENAMES = [
    "apps_entity", "models_entity",
    "addApp_entity", "removeApp_entity",
    "addModel_entity", "removeModel_entity",
]


def _demo_content_type():
    from dev.demo.models import Product
    return ContentType.objects.get_for_model(Product)


def _grant_entity_action_permissions(root_group):
    """Same documented gap/workaround as hr/tests/test_hr_phase2.py's
    _grant_check_in_out and notifications/tests/test_actions.py's
    _grant_outbox_action_permissions:

    1. The one-time post_migrate sync that built the test DB ran
       before django_resaas.saas.data.entity.views.entity was ever
       imported, so VIEW_REGISTRY didn't have EntityAPIView yet and
       these Permission rows were never created - re-import + re-sync
       here.
    2. Even once the Permission rows exist, ActionSyncService never
       auto-grants custom-action permissions to any group - granting
       is a deliberate, separate admin step in this framework."""

    import django_resaas.saas.data.entity.views.entity  # noqa: F401 - populate VIEW_REGISTRY
    from django.contrib.auth.models import Permission
    from django_resaas.saas.core.base.registry import VIEW_REGISTRY
    from django_resaas.saas.core.services.action_sync_service import ActionSyncService

    ActionSyncService.sync_registry(VIEW_REGISTRY)

    permissions = Permission.objects.filter(codename__in=ENTITY_ACTION_CODENAMES)
    root_group.permissions.add(*permissions)


def _guest_client(tenant):
    """Same pattern used in test_dashboard_engine.py for 'no
    permission' tests - a fresh, per-entity Guest group (Group.name is
    globally unique, so a plain 'Guest' would leak whatever another
    test already granted it) with no permissions at all."""
    guest_group, _ = Group.objects.get_or_create(name=f"Guest-{tenant['entity'].id}")

    BranchUserGroup.objects.get_or_create(
        user=tenant["user"], branch=tenant["branch"], group=guest_group,
        defaults={"state": "Active"},
    )

    context = ResaasContextService.issue(
        user=tenant["user"], entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id, group_id=guest_group.id,
    )

    client = APIClient()
    client.force_authenticate(user=tenant["user"])
    client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")
    return client


class TestEntityAddApp:

    def test_add_app_succeeds_when_already_linked_to_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addapp-ok")
        _grant_entity_action_permissions(tenant["root_group"])
        entity = tenant["entity"]
        app = App.objects.create(name="billing")
        EntityTypeApp.objects.create(entity_type=entity.entity_type, app=app)

        response = tenant["client"].post(
            f"/api/django_resaas/entitys/{entity.id}/addApp/",
            {"id": str(app.id)},
        )

        assert response.status_code == 201, response.data
        entity_app = EntityApp.objects.get(entity=entity, app=app)
        # TimeModel.state defaults to "Inactive" - get_or_create() without
        # defaults={"state": "Active"} silently created a linked-but-
        # inactive row (is_module_active() checks state="Active"
        # specifically, so the app never actually activated).
        assert entity_app.state == "Active"

    def test_add_app_rejected_when_not_part_of_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addapp-scope")
        _grant_entity_action_permissions(tenant["root_group"])
        entity = tenant["entity"]
        app = App.objects.create(name="reporting")
        # deliberately no EntityTypeApp for this app

        response = tenant["client"].post(
            f"/api/django_resaas/entitys/{entity.id}/addApp/",
            {"id": str(app.id)},
        )

        assert response.status_code == 400
        assert not EntityApp.objects.filter(entity=entity, app=app).exists()

    def test_remove_app_deletes_the_entity_app_row(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-removeapp")
        _grant_entity_action_permissions(tenant["root_group"])
        entity = tenant["entity"]
        app = App.objects.create(name="billing")
        EntityTypeApp.objects.create(entity_type=entity.entity_type, app=app)
        EntityApp.objects.create(entity=entity, app=app)

        response = tenant["client"].post(
            f"/api/django_resaas/entitys/{entity.id}/removeApp/",
            {"id": str(app.id)},
        )

        assert response.status_code == 200
        assert not EntityApp.objects.filter(entity=entity, app=app).exists()

    def test_apps_list_reflects_current_state(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-apps-list")
        _grant_entity_action_permissions(tenant["root_group"])
        entity = tenant["entity"]
        app = App.objects.create(name="billing")
        EntityTypeApp.objects.create(entity_type=entity.entity_type, app=app)
        EntityApp.objects.create(entity=entity, app=app)

        response = tenant["client"].get(f"/api/django_resaas/entitys/{entity.id}/apps/")

        assert response.status_code == 200
        # BootstrapService itself already activates django_resaas/hr/
        # notifications for every new tenant (see bootstrap_service.py)
        # - this list is not exclusive to what this test just created,
        # only membership matters here.
        assert app.id in {row["id"] for row in response.data}


class TestEntityAppsPermission:

    def test_add_app_without_permission_returns_403(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addapp-noperm")
        entity = tenant["entity"]
        app = App.objects.create(name="billing")
        EntityTypeApp.objects.create(entity_type=entity.entity_type, app=app)
        client = _guest_client(tenant)

        response = client.post(
            f"/api/django_resaas/entitys/{entity.id}/addApp/",
            {"id": str(app.id)},
        )

        assert response.status_code == 403
        assert not EntityApp.objects.filter(entity=entity, app=app).exists()

    def test_list_apps_without_permission_returns_403(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-listapps-noperm")
        entity = tenant["entity"]
        client = _guest_client(tenant)

        response = client.get(f"/api/django_resaas/entitys/{entity.id}/apps/")

        assert response.status_code == 403


class TestEntityAddModelScope:

    def test_add_model_succeeds_when_already_linked_to_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addmodel-ok")
        _grant_entity_action_permissions(tenant["root_group"])
        entity = tenant["entity"]
        ct = _demo_content_type()
        EntityTypeModel.objects.create(entity_type=entity.entity_type, model=ct)

        response = tenant["client"].post(
            f"/api/django_resaas/entitys/{entity.id}/addModel/",
            {"id": str(ct.id)},
        )

        assert response.status_code == 201, response.data
        entity_model = EntityModel.objects.get(entity=entity, model=ct)
        assert entity_model.state == "Active"

    def test_add_model_rejected_when_not_part_of_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addmodel-scope")
        _grant_entity_action_permissions(tenant["root_group"])
        entity = tenant["entity"]
        ct = _demo_content_type()
        # deliberately no EntityTypeModel for this content type

        response = tenant["client"].post(
            f"/api/django_resaas/entitys/{entity.id}/addModel/",
            {"id": str(ct.id)},
        )

        assert response.status_code == 400
        assert not EntityModel.objects.filter(entity=entity, model=ct).exists()

    def test_add_model_without_permission_returns_403(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addmodel-noperm")
        entity = tenant["entity"]
        ct = _demo_content_type()
        EntityTypeModel.objects.create(entity_type=entity.entity_type, model=ct)
        client = _guest_client(tenant)

        response = client.post(
            f"/api/django_resaas/entitys/{entity.id}/addModel/",
            {"id": str(ct.id)},
        )

        assert response.status_code == 403
        assert not EntityModel.objects.filter(entity=entity, model=ct).exists()


class TestEntityTypeAddAppAddModelState:
    """Same "state defaults to Inactive" bug, one level up
    (EntityTypeAPIView.addApp/addModel) - see views/entity_type.py."""

    def test_add_app_activates_the_entity_type_app_row(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entitytype-addapp-state")
        entity_type = tenant["entity"].entity_type
        app = App.objects.create(name="billing")

        response = tenant["client"].post(
            f"/api/django_resaas/entitytypes/{entity_type.id}/addApp/",
            {"id": str(app.id)},
        )

        assert response.status_code == 201, response.data
        entity_type_app = EntityTypeApp.objects.get(entity_type=entity_type, app=app)
        assert entity_type_app.state == "Active"

    def test_add_model_activates_the_entity_type_model_and_entity_model_rows(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entitytype-addmodel-state")
        entity = tenant["entity"]
        ct = _demo_content_type()

        response = tenant["client"].post(
            f"/api/django_resaas/entitytypes/{entity.entity_type.id}/addModel/",
            {"id": str(ct.id)},
        )

        assert response.status_code == 201, response.data
        entity_type_model = EntityTypeModel.objects.get(entity_type=entity.entity_type, model=ct)
        assert entity_type_model.state == "Active"

        # addModel also activates the model for every existing Entity of
        # this EntityType (see views/entity_type.py) - same bug applied
        # there too.
        entity_model = EntityModel.objects.get(entity=entity, model=ct)
        assert entity_model.state == "Active"
