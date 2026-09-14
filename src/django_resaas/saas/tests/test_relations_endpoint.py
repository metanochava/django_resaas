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
        permission = Permission.objects.first()
        assert permission is not None

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
