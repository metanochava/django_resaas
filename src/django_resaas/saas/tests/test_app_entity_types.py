"""AppAPIView.entityTypes/addEntityType/removeEntityType - mesma
relação/idioma já usado do lado inverso por EntityTypeAPIView.apps/
addApp/removeApp (django_resaas.saas.data.entity_type.views.entity_type),
só invertido: em vez de "quais Apps tem este EntityType", "quais
EntityTypes têm esta App" - mesmo modelo EntityTypeApp, sem nenhuma
tabela/relação nova."""
import pytest

from django_resaas.saas.models.app import App
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity_type_app import EntityTypeApp

pytestmark = pytest.mark.django_db


class TestAppEntityTypes:

    def test_entity_types_lists_only_linked_entity_types(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-entitytypes-list")
        client = tenant["client"]

        app = App.objects.create(name="billing")
        linked_type = tenant["entity"].entity_type
        other_type = EntityType.objects.create(name="Other Type")

        EntityTypeApp.objects.create(entity_type=linked_type, app=app)

        response = client.get(f"/api/django_resaas/apps/{app.id}/entityTypes/")

        assert response.status_code == 200
        ids = {row["id"] for row in response.data}
        assert str(linked_type.id) in {str(i) for i in ids}
        assert other_type.id not in ids

    def test_add_entity_type_creates_relation(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-entitytypes-add")
        client = tenant["client"]

        app = App.objects.create(name="billing")
        entity_type = tenant["entity"].entity_type

        assert not EntityTypeApp.objects.filter(app=app, entity_type=entity_type).exists()

        response = client.post(
            f"/api/django_resaas/apps/{app.id}/addEntityType/",
            {"id": str(entity_type.id)},
        )

        assert response.status_code == 201
        assert EntityTypeApp.objects.filter(app=app, entity_type=entity_type).exists()

    def test_add_entity_type_is_idempotent(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-entitytypes-add-twice")
        client = tenant["client"]

        app = App.objects.create(name="billing")
        entity_type = tenant["entity"].entity_type

        for _ in range(2):
            response = client.post(
                f"/api/django_resaas/apps/{app.id}/addEntityType/",
                {"id": str(entity_type.id)},
            )
            assert response.status_code == 201

        assert EntityTypeApp.objects.filter(app=app, entity_type=entity_type).count() == 1

    def test_add_entity_type_unknown_id_fails(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-entitytypes-add-unknown")
        client = tenant["client"]

        app = App.objects.create(name="billing")

        response = client.post(
            f"/api/django_resaas/apps/{app.id}/addEntityType/",
            {"id": "00000000-0000-0000-0000-000000000000"},
        )

        assert response.status_code == 400

    def test_remove_entity_type_deletes_relation(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-entitytypes-remove")
        client = tenant["client"]

        app = App.objects.create(name="billing")
        entity_type = tenant["entity"].entity_type
        EntityTypeApp.objects.create(entity_type=entity_type, app=app)

        response = client.post(
            f"/api/django_resaas/apps/{app.id}/removeEntityType/",
            {"id": str(entity_type.id)},
        )

        assert response.status_code == 200
        assert not EntityTypeApp.objects.filter(app=app, entity_type=entity_type).exists()

    def test_remove_entity_type_never_touches_other_apps(self, bootstrap_tenant):
        """Remover a relação para uma App nunca deve afectar a relação
        do mesmo EntityType com outra App - o filtro tem de incluir
        sempre app=, nunca só entity_type_id=."""
        tenant = bootstrap_tenant("app-entitytypes-remove-scoped")
        client = tenant["client"]

        app_a = App.objects.create(name="billing")
        app_b = App.objects.create(name="reporting")
        entity_type = tenant["entity"].entity_type

        EntityTypeApp.objects.create(entity_type=entity_type, app=app_a)
        EntityTypeApp.objects.create(entity_type=entity_type, app=app_b)

        response = client.post(
            f"/api/django_resaas/apps/{app_a.id}/removeEntityType/",
            {"id": str(entity_type.id)},
        )

        assert response.status_code == 200
        assert not EntityTypeApp.objects.filter(app=app_a, entity_type=entity_type).exists()
        assert EntityTypeApp.objects.filter(app=app_b, entity_type=entity_type).exists()
