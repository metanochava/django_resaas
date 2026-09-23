"""BaseAdmin bulk actions: Activate / Deactivate next to Soft delete / Restore,
each labelled with the model name ("... selected departments"), translated
per request language, and only offered when the model has the field they use."""
import pytest
from django.contrib import admin
from django.test import RequestFactory

from django_resaas.hr.models.department import Department

pytestmark = pytest.mark.django_db


def _request(user, lang=None):
    extra = {"HTTP_L": lang} if lang else {}
    request = RequestFactory().get("/", **extra)
    user.is_superuser = True  # in memory only: the admin permission checks are not what is tested
    request.user = user
    return request


def _department_admin():
    return admin.site._registry[Department]


def _labels(model_admin, request):
    return {value: label for value, label in model_admin.get_action_choices(request)}


def test_actions_are_labelled_with_the_model_name(bootstrap_tenant):
    tenant = bootstrap_tenant("admin-actions-labels")
    labels = _labels(_department_admin(), _request(tenant["user"]))

    assert labels["activate_selected"] == "Activate selected departments"
    assert labels["deactivate_selected"] == "Deactivate selected departments"
    assert labels["soft_delete_selected"] == "Soft delete selected departments"
    assert labels["restore_selected"] == "Restore selected departments"


def test_labels_are_translated_with_the_model_name_last(bootstrap_tenant):
    tenant = bootstrap_tenant("admin-actions-i18n")
    labels = _labels(_department_admin(), _request(tenant["user"], lang="pt-pt"))

    assert labels["activate_selected"] == "Activar departments seleccionados"
    assert labels["deactivate_selected"] == "Desactivar departments seleccionados"


def test_activate_and_deactivate_change_state_and_record_the_actor(bootstrap_tenant):
    tenant = bootstrap_tenant("admin-actions-state")
    department = Department.objects.create(entity=tenant["entity"], branch=tenant["branch"], name="Ops")
    department.refresh_from_db()
    assert department.state == "Inactive"  # TimeModel default

    model_admin = _department_admin()
    request = _request(tenant["user"])
    queryset = Department.all_objects.filter(pk=department.pk)

    from django_resaas.saas.core.base.admin import activate_selected, deactivate_selected

    activate_selected(model_admin, request, queryset)
    department.refresh_from_db()
    assert department.state == "Active"
    assert department.updated_by_id == tenant["user"].id

    deactivate_selected(model_admin, request, queryset)
    department.refresh_from_db()
    assert department.state == "Inactive"


def test_soft_delete_and_restore_still_work(bootstrap_tenant):
    from django_resaas.saas.core.base.admin import restore_selected, soft_delete_selected

    tenant = bootstrap_tenant("admin-actions-softdelete")
    department = Department.objects.create(entity=tenant["entity"], branch=tenant["branch"], name="Ops")
    model_admin = _department_admin()
    request = _request(tenant["user"])
    queryset = Department.all_objects.filter(pk=department.pk)

    soft_delete_selected(model_admin, request, queryset)
    assert Department.all_objects.get(pk=department.pk).deleted_at is not None

    restore_selected(model_admin, request, queryset)
    assert Department.all_objects.get(pk=department.pk).deleted_at is None


def test_an_action_is_not_offered_when_the_model_lacks_its_field(bootstrap_tenant):
    from django_resaas.saas.core.base.admin import BaseAdmin
    from django_resaas.saas.models.language import Language

    tenant = bootstrap_tenant("admin-actions-missing-field")
    fields = {f.name for f in Language._meta.fields}
    model_admin = BaseAdmin(Language, admin.site)
    offered = set(model_admin.get_actions(_request(tenant["user"])))

    assert ("activate_selected" in offered) == ("state" in fields)
    assert ("restore_selected" in offered) == ("deleted_at" in fields)


# ---- objects created through the API are Active by default (views, not BaseModel) ----

def test_created_through_the_api_is_active_by_default(bootstrap_tenant):
    tenant = bootstrap_tenant("api-create-active", modules=("hr",))

    response = tenant["client"].post("/api/hr/departments/", {"name": "Finance"}, format="json")

    assert response.status_code == 201
    assert Department.objects.get(pk=response.data["id"]).state == "Active"


def test_an_explicit_state_from_the_client_is_respected(bootstrap_tenant):
    tenant = bootstrap_tenant("api-create-explicit", modules=("hr",))

    response = tenant["client"].post("/api/hr/departments/", {"name": "Legal", "state": "Inactive"}, format="json")

    assert response.status_code == 201
    assert Department.objects.get(pk=response.data["id"]).state == "Inactive"


def test_the_model_default_is_unchanged():
    assert Department._meta.get_field("state").default == "Inactive"
    assert Department(name="x").state == "Inactive"
