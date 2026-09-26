"""RelationsAPIView (GET /api/django_resaas/relations/?model=app.Model)
- generic label/value lookup for a relation picker (s-select :api=...).

Used against models that DON'T inherit LabelValueMixin too - e.g. an
admin picking an auth.Permission to grant to a Group (see
grant_root_action_permissions.py) hits this with model=auth.Permission.
Permission/Group/ContentType are plain Django models, not RESAAS ones,
so get_value()/get_label() don't exist on them - the view must fall
back to pk/str() instead of assuming every model has these methods."""
import pytest

from django.contrib.auth.models import Permission

pytestmark = pytest.mark.django_db


class TestRelationsEndpoint:

    def test_non_resaas_model_falls_back_to_pk_and_str(self, bootstrap_tenant):
        """auth.Permission has neither get_value()/get_label() nor the
        LabelValueMixin methods those call internally - this used to
        raise AttributeError: 'Permission' object has no attribute
        'get_label_field'."""
        tenant = bootstrap_tenant("relations-permission")

        # The endpoint only returns the 50 most recent rows (order_by
        # "-id"), and the test DB already has hundreds of permissions -
        # create one explicitly instead of assuming Permission.objects.
        # first() lands in that slice.
        permission = Permission.objects.create(
            codename="a_pk_and_str_fallback_test_permission",
            name="A pk/str fallback test permission",
            content_type=Permission.objects.first().content_type,
        )

        response = tenant["client"].get(
            "/api/django_resaas/relations/?format=json&model=auth.Permission"
        )

        assert response.status_code == 200, response.data
        row = next(r for r in response.data if r["id"] == permission.pk)
        assert row["value"] == permission.pk
        assert row["label"] == str(permission)

    def test_search_by_codename_still_works_for_non_resaas_model(self, bootstrap_tenant):
        tenant = bootstrap_tenant("relations-permission-search")
        permission = Permission.objects.create(
            codename="a_very_specific_test_codename",
            name="A very specific test permission",
            content_type=Permission.objects.first().content_type,
        )

        response = tenant["client"].get(
            "/api/django_resaas/relations/"
            "?format=json&model=auth.Permission&search=a_very_specific_test_codename"
        )

        assert response.status_code == 200, response.data
        assert any(r["id"] == permission.pk for r in response.data)

    def test_resaas_model_keeps_using_its_own_label_field(self, bootstrap_tenant):
        """A real RESAAS model (LabelValueMixin) must keep using its own
        get_value()/get_label() - this endpoint's fallback is only for
        models that don't have them."""
        tenant = bootstrap_tenant("relations-entitytype")
        entity_type = tenant["entity"].entity_type

        response = tenant["client"].get(
            "/api/django_resaas/relations/?format=json&model=django_resaas.EntityType"
        )

        assert response.status_code == 200, response.data
        row = next(r for r in response.data if r["id"] == entity_type.pk)
        assert row["label"] == entity_type.get_label()


def _client_with(tenant, codenames):
    """A client whose group has only `codenames` in the tenant's Branch."""
    import uuid

    from rest_framework.test import APIClient

    from django_resaas.saas.core.tenant.context import ResaasContextService
    from django_resaas.saas.models.branch_user_group import BranchUserGroup
    from django_resaas.saas.models.group import Group

    group = Group.objects.create(name=f"Picker-{uuid.uuid4().hex[:12]}")
    permissions = Permission.objects.filter(codename__in=codenames)
    assert permissions.count() >= len(set(codenames)) or not codenames, codenames
    group.permissions.add(*permissions)
    BranchUserGroup.objects.create(user=tenant["user"], branch=tenant["branch"], group=group)

    context = ResaasContextService.issue(
        user=tenant["user"], entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id, group_id=group.id,
    )
    client = APIClient()
    client.force_authenticate(user=tenant["user"])
    client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")
    return client


USERS = "/api/django_resaas/relations/?format=json&model=django_resaas.User"


class TestRelationPicker:
    """A picker returns {id, value, label} only: it is allowed with the
    model's list/view permission OR the permission to write a form with a
    field pointing to it - and always only the current Entity's rows."""

    def test_writing_a_form_that_references_the_model_is_enough(self, bootstrap_tenant):
        tenant = bootstrap_tenant("picker-writer")
        # BranchUserGroup.user -> User: whoever assigns users to groups picks users
        client = _client_with(tenant, ["add_branchusergroup"])

        response = client.get(USERS)

        assert response.status_code == 200, response.data
        assert {r["id"] for r in response.data} >= {tenant["user"].id}
        assert set(response.data[0]) == {"id", "value", "label"}

    def test_audit_columns_do_not_count(self, bootstrap_tenant):
        """created_by/updated_by point to User on every model: writing any
        record is not a reason to list the Entity's users."""
        tenant = bootstrap_tenant("picker-audit")
        client = _client_with(tenant, ["add_entitytype"])

        response = client.get(USERS)

        assert response.status_code == 403
        assert set(response.data) == {"error"}

    def test_without_any_related_permission_it_is_403(self, bootstrap_tenant):
        tenant = bootstrap_tenant("picker-none")

        assert _client_with(tenant, []).get(USERS).status_code == 403

    def test_users_are_only_those_of_the_current_entity(self, bootstrap_tenant):
        tenant = bootstrap_tenant("picker-mine")
        other = bootstrap_tenant("picker-theirs")
        client = _client_with(tenant, ["list_user"])

        ids = {r["id"] for r in client.get(USERS).data}

        assert tenant["user"].id in ids
        assert other["user"].id not in ids

    def test_a_malformed_model_is_400_with_the_field(self, bootstrap_tenant):
        tenant = bootstrap_tenant("picker-bad")

        response = tenant["client"].get("/api/django_resaas/relations/?format=json&model=User")

        assert response.status_code == 400
        assert "model" in response.data["error"]["details"]
