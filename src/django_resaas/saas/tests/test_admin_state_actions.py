"""BaseAdmin bulk actions: Activate / Deactivate next to Soft delete / Restore,
each labelled with the model name ("... selected categories"), translated
per request language, and only offered when the model has the field they use."""
import pytest
from django.contrib import admin
from django.test import RequestFactory

from dev.demo.models import Category

pytestmark = pytest.mark.django_db


def _request(user, lang=None):
    extra = {"HTTP_L": lang} if lang else {}
    request = RequestFactory().get("/", **extra)
    user.is_superuser = True  # in memory only: the admin permission checks are not what is tested
    request.user = user
    return request


def _category_admin():
    return admin.site._registry[Category]


def _labels(model_admin, request):
    return {value: label for value, label in model_admin.get_action_choices(request)}


def test_actions_are_labelled_with_the_model_name(bootstrap_tenant):
    tenant = bootstrap_tenant("admin-actions-labels")
    labels = _labels(_category_admin(), _request(tenant["user"]))

    assert labels["activate_selected"] == "Activate selected categories"
    assert labels["deactivate_selected"] == "Deactivate selected categories"
    assert labels["soft_delete_selected"] == "Soft delete selected categories"
    assert labels["restore_selected"] == "Restore selected categories"


def test_labels_are_translated_with_the_model_name_last(bootstrap_tenant):
    tenant = bootstrap_tenant("admin-actions-i18n")
    labels = _labels(_category_admin(), _request(tenant["user"], lang="pt-pt"))

    assert labels["activate_selected"] == "Activar categories seleccionados"
    assert labels["deactivate_selected"] == "Desactivar categories seleccionados"


def test_activate_and_deactivate_change_state_and_record_the_actor(bootstrap_tenant):
    tenant = bootstrap_tenant("admin-actions-state")
    category = Category.objects.create(entity=tenant["entity"], branch=tenant["branch"], name="Ops")
    category.refresh_from_db()
    assert category.state == "Inactive"  # TimeModel default

    model_admin = _category_admin()
    request = _request(tenant["user"])
    queryset = Category.all_objects.filter(pk=category.pk)

    from django_resaas.saas.core.base.admin import activate_selected, deactivate_selected

    activate_selected(model_admin, request, queryset)
    category.refresh_from_db()
    assert category.state == "Active"
    assert category.updated_by_id == tenant["user"].id

    deactivate_selected(model_admin, request, queryset)
    category.refresh_from_db()
    assert category.state == "Inactive"


def test_soft_delete_and_restore_still_work(bootstrap_tenant):
    from django_resaas.saas.core.base.admin import restore_selected, soft_delete_selected

    tenant = bootstrap_tenant("admin-actions-softdelete")
    category = Category.objects.create(entity=tenant["entity"], branch=tenant["branch"], name="Ops")
    model_admin = _category_admin()
    request = _request(tenant["user"])
    queryset = Category.all_objects.filter(pk=category.pk)

    soft_delete_selected(model_admin, request, queryset)
    assert Category.all_objects.get(pk=category.pk).deleted_at is not None

    restore_selected(model_admin, request, queryset)
    assert Category.all_objects.get(pk=category.pk).deleted_at is None


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
    tenant = bootstrap_tenant("api-create-active", modules=("demo",))

    response = tenant["client"].post("/api/demo/categories/", {"name": "Finance"}, format="json")

    assert response.status_code == 201
    assert Category.objects.get(pk=response.data["id"]).state == "Active"


def test_an_explicit_state_from_the_client_is_respected(bootstrap_tenant):
    tenant = bootstrap_tenant("api-create-explicit", modules=("demo",))

    response = tenant["client"].post("/api/demo/categories/", {"name": "Legal", "state": "Inactive"}, format="json")

    assert response.status_code == 201
    assert Category.objects.get(pk=response.data["id"]).state == "Inactive"


def test_the_model_default_is_unchanged():
    assert Category._meta.get_field("state").default == "Inactive"
    assert Category(name="x").state == "Inactive"
