"""EntityAPIView.addApp/removeApp (new) and addModel (now validated) -
an Entity may only activate an App/Model that its own EntityType
already has (EntityTypeApp/EntityTypeModel) - the EntityType defines
the available universe, the Entity just picks within it. Mirrors the
already-existing EntityTypeAPIView.addApp/addModel validation-free
"EntityType picks from the global App/ContentType registry" level,
one level down."""
import pytest
from django.contrib.contenttypes.models import ContentType

from django_resaas.saas.models.app import App
from django_resaas.saas.models.entity_app import EntityApp
from django_resaas.saas.models.entity_model import EntityModel
from django_resaas.saas.models.entity_type_app import EntityTypeApp
from django_resaas.saas.models.entity_type_model import EntityTypeModel

pytestmark = pytest.mark.django_db


def _demo_content_type():
    from dev.demo.models import Product
    return ContentType.objects.get_for_model(Product)


class TestEntityAddApp:

    def test_add_app_succeeds_when_already_linked_to_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addapp-ok")
        entity = tenant["entity"]
        app = App.objects.create(name="billing")
        EntityTypeApp.objects.create(entity_type=entity.entity_type, app=app)

        response = tenant["client"].post(
            f"/api/django_resaas/entitys/{entity.id}/addApp/",
            {"id": str(app.id)},
        )

        assert response.status_code == 201, response.data
        assert EntityApp.objects.filter(entity=entity, app=app).exists()

    def test_add_app_rejected_when_not_part_of_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addapp-scope")
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


class TestEntityAddModelScope:

    def test_add_model_succeeds_when_already_linked_to_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addmodel-ok")
        entity = tenant["entity"]
        ct = _demo_content_type()
        EntityTypeModel.objects.create(entity_type=entity.entity_type, model=ct)

        response = tenant["client"].post(
            f"/api/django_resaas/entitys/{entity.id}/addModel/",
            {"id": str(ct.id)},
        )

        assert response.status_code == 201, response.data
        assert EntityModel.objects.filter(entity=entity, model=ct).exists()

    def test_add_model_rejected_when_not_part_of_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("entity-addmodel-scope")
        entity = tenant["entity"]
        ct = _demo_content_type()
        # deliberately no EntityTypeModel for this content type

        response = tenant["client"].post(
            f"/api/django_resaas/entitys/{entity.id}/addModel/",
            {"id": str(ct.id)},
        )

        assert response.status_code == 400
        assert not EntityModel.objects.filter(entity=entity, model=ct).exists()
