"""Generic relation engine (backend half): schema metadata, preview-aware
select search, tenant isolation and permissions - proven on Person (a card
relation), on a non-Person tenant model (dev.demo Product, hr JobPosition)
and on a many-to-many, so nothing here is Person-specific."""
import pytest
from unittest import mock

from rest_framework.test import APIRequestFactory

from django_resaas.saas.core.utils.relation_preview import (
    build_preview_item,
    get_relation_preview_config,
    preview_select_related,
)
from django_resaas.saas.management.apicommands.view.app_schema import _schema_fields
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


def _field(fields, name):
    return next(f for f in fields if f["name"] == name)


# ---------------------------------------------------------------- schema

class TestRelationSchema:

    def test_person_relation_is_a_card_with_its_declared_preview(self):
        from django_resaas.hr.models.employee import Employee

        config = _field(_schema_fields(Employee), "person")["relation_config"]

        assert config["variant"] == "card"
        assert config["preview"] == {
            "title": "full_name",
            "subtitle": ["email", "phone"],
            "avatar": "photo",
            "meta": ["date_of_birth", "nationality"],
        }
        assert config["permissions"] == {
            "list": "list_person", "add": "add_person", "change": "change_person", "view": "view_person",
        }

    def test_same_person_relation_on_another_model_needs_no_extra_config(self):
        """Patient/Student/Customer-style models reuse it purely by pointing at Person."""
        from django_resaas.hr.models.employee import Employee

        other = [f for f in _schema_fields(Employee) if f.get("relation_config", {}).get("model") == "Person"]

        assert other and all(f["relation_config"]["variant"] == "card" for f in other)

    def test_relation_without_declared_preview_stays_the_lightweight_select(self):
        from django_resaas.hr.models.employee import Employee

        config = _field(_schema_fields(Employee), "position")["relation_config"]

        assert config["variant"] == "select"
        assert "preview" not in config
        # existing keys are untouched (backward compatible)
        assert {"app", "model", "endpoint"} <= set(config)
        assert {"add", "change", "view"} <= set(config["permissions"])

    def test_many_to_many_never_gets_the_single_selection_card(self, monkeypatch):
        from django_resaas.saas.models.group import Group

        monkeypatch.setattr(Group._meta.get_field("permissions").related_model, "RESAAS", type(
            "RESAAS", (), {"preview": {"title": "name"}}), raising=False)

        config = _field(_schema_fields(Group), "permissions")["relation_config"]

        assert config["variant"] == "select"


# ---------------------------------------------------------------- preview config

class TestPreviewConfig:

    def test_no_declaration_means_no_preview(self):
        from dev.demo.models import Product

        assert get_relation_preview_config(Product) is None

    def test_only_real_fields_are_kept(self):
        from dev.demo.models import Product

        with mock.patch.object(Product, "RESAAS", type("RESAAS", (), {
            "preview": {"title": "name", "subtitle": ["sku", "nope"], "avatar": "name", "meta": ["price", "a__b"]},
        })):
            config = get_relation_preview_config(Product)

        assert config == {"title": "name", "subtitle": ["sku"], "avatar": None, "meta": ["price"]}

    def test_item_is_bounded_to_the_declared_fields(self):
        person = Person.objects.create(name="Ana", surname="Costa", email="ana@example.com", phone="841110000", nationality="MZ")

        item = build_preview_item(person, get_relation_preview_config(Person))

        assert item["title"] == "Ana Costa"
        assert item["subtitle"] == ["ana@example.com", "841110000"]
        assert item["avatar"] is None
        assert item["meta"] == [{"field": "nationality", "label": "Nationality", "value": "MZ"}]

    def test_dotted_paths_are_select_related(self):
        from django_resaas.hr.models.employee import Employee

        config = {"title": "person__full_name", "subtitle": ["position__title"], "avatar": None, "meta": []}

        assert preview_select_related(Employee, config) == ["person", "position"]


# ---------------------------------------------------------------- select API

class TestPreviewSelectApi:

    def test_person_search_returns_rich_rows_only_when_asked(self, bootstrap_tenant):
        tenant = bootstrap_tenant("relation-person-preview")
        person = Person.objects.create(name="Metano", surname="Chavana", email="metano@example.com", phone="841234567")

        plain = tenant["client"].get("/api/django_resaas/persons/?select=true&search=Metano")
        rich = tenant["client"].get("/api/django_resaas/persons/?select=true&preview=true&search=Metano")

        assert plain.status_code == 200 and rich.status_code == 200

        plain_row = next(r for r in plain.data["results"] if r["value"] == person.id)
        rich_row = next(r for r in rich.data["results"] if r["value"] == person.id)

        assert "preview" not in plain_row
        assert plain_row["label"] == "Metano Chavana"
        assert rich_row["id"] == person.id
        assert rich_row["preview"]["title"] == "Metano Chavana"
        assert rich_row["preview"]["subtitle"] == ["metano@example.com", "841234567"]

    def test_search_uses_the_related_models_own_search_fields(self, bootstrap_tenant):
        tenant = bootstrap_tenant("relation-person-search")
        Person.objects.create(name="Zed", surname="Quux", phone="850000123")

        response = tenant["client"].get("/api/django_resaas/persons/?select=true&preview=true&search=850000123")

        assert [r["label"] for r in response.data["results"]] == ["Zed Quux"]

    def test_one_record_can_be_looked_up_by_id_with_its_preview(self, bootstrap_tenant):
        """How the picker shows a value it loaded without a preview."""
        tenant = bootstrap_tenant("relation-person-by-id")
        person = Person.objects.create(name="Lookup", surname="Target", email="lookup@example.com")
        Person.objects.create(name="Lookup", surname="Other")

        response = tenant["client"].get(f"/api/django_resaas/persons/?select=true&preview=true&id={person.id}")

        assert [r["value"] for r in response.data["results"]] == [person.id]
        assert response.data["results"][0]["preview"]["subtitle"] == ["lookup@example.com"]

    def test_results_are_paginated(self, bootstrap_tenant):
        tenant = bootstrap_tenant("relation-person-page")
        for i in range(5):
            Person.objects.create(name=f"Pagey{i}", surname="Row")

        response = tenant["client"].get("/api/django_resaas/persons/?select=true&preview=true&search=Pagey&page_size=2")

        assert response.status_code == 200
        assert len(response.data["results"]) == 2
        assert response.data["next"]

    def test_a_non_person_model_uses_the_same_endpoint_and_stays_label_only(self, bootstrap_tenant, create_product):
        tenant = bootstrap_tenant("relation-product", modules=("demo",))
        create_product(tenant["client"], name="Widget", sku="W-1")

        response = tenant["client"].get("/api/demo/products/?select=true&preview=true&search=Widget")

        assert response.status_code == 200
        assert [r["label"] for r in response.data["results"]] == ["Widget"]
        assert "preview" not in response.data["results"][0]

    def test_a_non_person_model_can_declare_its_own_preview(self, bootstrap_tenant, create_product):
        from dev.demo.models import Product

        tenant = bootstrap_tenant("relation-product-card", modules=("demo",))
        create_product(tenant["client"], name="Widget", sku="W-1", price="9.99")

        with mock.patch.object(Product, "RESAAS", type("RESAAS", (), {
            "label_field": "name", "search_fields": ["name", "sku"], "crud": True,
            "preview": {"subtitle": ["sku"], "meta": ["price"]},
        })):
            response = tenant["client"].get("/api/demo/products/?select=true&preview=true&search=Widget")

        row = response.data["results"][0]
        assert row["preview"]["title"] == "Widget"
        assert row["preview"]["subtitle"] == ["W-1"]
        assert row["preview"]["meta"][0]["value"] == "9.99"

    def test_another_entitys_rows_are_not_discoverable(self, bootstrap_tenant, create_product):
        mine = bootstrap_tenant("relation-iso-a", modules=("demo",))
        theirs = bootstrap_tenant("relation-iso-b", modules=("demo",))
        create_product(theirs["client"], name="Secret Widget", sku="S-1")

        response = mine["client"].get("/api/demo/products/?select=true&preview=true&search=Secret")

        assert response.status_code == 200
        assert response.data["results"] == []


# ---------------------------------------------------------------- generic /relations/ endpoint

class TestRelationsEndpointIsTenantSafe:

    def test_only_the_current_entitys_rows_are_returned(self, bootstrap_tenant, create_product):
        mine = bootstrap_tenant("relations-iso-a", modules=("demo",))
        theirs = bootstrap_tenant("relations-iso-b", modules=("demo",))
        create_product(mine["client"], name="Mine Widget", sku="M-1")
        create_product(theirs["client"], name="Theirs Widget", sku="T-1")

        response = mine["client"].get("/api/django_resaas/relations/?format=json&model=demo.Product")

        assert response.status_code == 200
        assert [r["label"] for r in response.data] == ["Mine Widget"]

    def test_a_resaas_model_needs_a_list_or_view_permission(self, bootstrap_tenant, create_product):
        tenant = bootstrap_tenant("relations-perm", modules=("demo",))
        create_product(tenant["client"], name="Widget", sku="W-1")

        with mock.patch(
            "django_resaas.saas.management.apicommands.view.app_schema.hasPermissionCode", return_value=False
        ):
            response = tenant["client"].get("/api/django_resaas/relations/?format=json&model=demo.Product")

        assert response.status_code == 403

    def test_view_permission_alone_is_enough(self, bootstrap_tenant, create_product):
        tenant = bootstrap_tenant("relations-perm-view", modules=("demo",))
        create_product(tenant["client"], name="Widget", sku="W-1")

        allowed = lambda request, role: role == "view_product"  # noqa: E731

        with mock.patch(
            "django_resaas.saas.management.apicommands.view.app_schema.hasPermissionCode", side_effect=allowed
        ):
            response = tenant["client"].get("/api/django_resaas/relations/?format=json&model=demo.Product")

        assert response.status_code == 200


# ---------------------------------------------------------------- tenant validation on assignment

class TestTenantRelationAssignment:

    def _request(self, entity):
        request = APIRequestFactory().post("/")
        request.entity_id = entity.id
        return request

    def _plain_serializer(self):
        """A serializer with NO hand-written tenant check - the mixin alone."""
        from django_resaas.hr.models.job_position import JobPosition
        from django_resaas.saas.core.base.serializers import BaseSerializer

        class PlainJobPositionSerializer(BaseSerializer):
            class Meta:
                model = JobPosition
                fields = ["title", "department"]

        return PlainJobPositionSerializer

    def _position(self, entity, branch, title):
        from django_resaas.hr.models.job_position import JobPosition

        return JobPosition.objects.create(title=title, entity=entity, branch=branch)

    def test_a_relation_from_another_entity_is_rejected(self, bootstrap_tenant):
        JobPositionSerializer = self._plain_serializer()

        mine = bootstrap_tenant("assign-a")
        theirs = bootstrap_tenant("assign-b")
        from django_resaas.hr.models.department import Department

        foreign = Department.objects.create(name="Foreign", entity=theirs["entity"], branch=theirs["branch"])

        serializer = JobPositionSerializer(
            data={"title": "Nurse", "department": foreign.id},
            context={"request": self._request(mine["entity"])},
        )

        assert not serializer.is_valid()
        assert "department" in serializer.errors

    def test_a_relation_from_the_current_entity_is_accepted(self, bootstrap_tenant):
        from django_resaas.hr.models.department import Department
        JobPositionSerializer = self._plain_serializer()

        mine = bootstrap_tenant("assign-own")
        own = Department.objects.create(name="Own", entity=mine["entity"], branch=mine["branch"])

        serializer = JobPositionSerializer(
            data={"title": "Nurse", "department": own.id},
            context={"request": self._request(mine["entity"])},
        )

        assert serializer.is_valid(), serializer.errors

    def test_person_relations_are_not_tenant_scoped(self, bootstrap_tenant):
        """Person is a global identity (no entity) - the guard must not reject it."""
        from django_resaas.hr.serializers.employee import EmployeeSerializer

        mine = bootstrap_tenant("assign-person")
        person = Person.objects.create(name="Global", surname="Person")

        serializer = EmployeeSerializer(
            data={"person": person.id},
            context={"request": self._request(mine["entity"])},
        )
        serializer.is_valid()

        assert "person" not in serializer.errors

    def test_no_tenant_context_means_no_check(self, bootstrap_tenant):
        from django_resaas.hr.models.department import Department
        JobPositionSerializer = self._plain_serializer()

        theirs = bootstrap_tenant("assign-none")
        foreign = Department.objects.create(name="Any", entity=theirs["entity"], branch=theirs["branch"])

        serializer = JobPositionSerializer(data={"title": "Nurse", "department": foreign.id}, context={})

        assert serializer.is_valid(), serializer.errors
