"""Two admin bugs reported live from /admin/django_resaas/group/?q=root:

1. `search_fields = ("__all__",)` (28 ModelAdmin classes in saas/admin.py,
   copy-pasted from the DRF serializer convention `fields = "__all__"`,
   which Django's ModelAdmin does not understand) crashed any search with
   `FieldError: Cannot resolve keyword '' into field` - Django splits the
   literal string "__all__" on "__" to resolve the ORM lookup path and
   gets an empty keyword. BaseAdmin.get_search_fields() now expands it to
   the model's real text fields.

2. Django's built-in auth.Group (from django.contrib.auth, always
   auto-registered in admin) duplicated RESAAS's own Group model in the
   admin sidebar - unregistered in saas/admin.py."""
import pytest
from django.contrib import admin
from django.contrib.auth.models import Group as DjangoAuthGroup
from django.test import RequestFactory

from django_resaas.saas.models.group import Group as ResaasGroup

pytestmark = pytest.mark.django_db


def test_django_auth_group_not_registered_in_admin():
    # saas.admin is already imported by the time pytest-django loads
    # urls/apps - autodiscover() (called during admin app startup)
    # would otherwise re-register it after saas.admin's own unregister
    # if import order won, so this also guards against that regression.
    admin.autodiscover()
    assert not admin.site.is_registered(DjangoAuthGroup)


def test_resaas_group_admin_all_search_fields_expands_to_real_fields():
    model_admin = admin.site._registry[ResaasGroup]
    fields = model_admin.get_search_fields(RequestFactory().get("/"))

    assert "__all__" not in fields
    assert "name" in fields


def test_resaas_group_admin_search_does_not_raise(bootstrap_tenant):
    bootstrap_tenant("admin-group-search")
    ResaasGroup.objects.create(name="root-admins")

    model_admin = admin.site._registry[ResaasGroup]
    request = RequestFactory().get("/admin/django_resaas/group/", {"q": "root"})

    qs, _ = model_admin.get_search_results(
        request, ResaasGroup.objects.all(), "root"
    )
    assert qs.filter(name="root-admins").exists()
