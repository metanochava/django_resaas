"""
Tests the shared BaseAPIView plumbing that isn't specific to any single
FASE 1 theme - see src/django_resaas/tests/ for tenant isolation, soft
delete, action sync, permission ownership and module activation, which
all moved there.
"""
import pytest

pytestmark = pytest.mark.django_db


def test_request_denied_without_permission(bootstrap_tenant):
    tenant = bootstrap_tenant("no-perms", modules=("demo",))

    # Guest group has no CRUD permissions granted to it (only Root does -
    # see core/signals/permissions.py's create_model_permissions)
    from django_resaas.saas.core.tenant.context import ResaasContextService
    from django_resaas.saas.models.group import Group

    guest_group = Group.objects.get(name="Guest")
    context = ResaasContextService.issue(
        user=tenant["user"],
        entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id,
        group_id=guest_group.id,
    )
    tenant["client"].credentials(
        HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1"
    )

    response = tenant["client"].get("/api/demo/products/")
    assert response.status_code == 403
    assert response.data["error"]["message"] == "Unauthorized"


def test_register_view_and_registerView_are_the_same_decorator():
    """register_view is the canonical name; registerView (camelCase) is the
    original name, kept as a supported alias because existing applications
    decorate their views with it - they must be the exact same object."""
    from django_resaas.saas.core.base.views import register_view, registerView

    assert registerView is register_view


def test_registerView_alias_still_registers_a_view():
    from django_resaas.saas.core.base.registry import VIEW_REGISTRY
    from django_resaas.saas.core.base.views import BaseAPIView, registerView

    @registerView("alias_things", module="alias_compat_test")
    class AliasThingAPIView(BaseAPIView):
        pass

    try:
        assert VIEW_REGISTRY["alias_compat_test"]["alias_things"] is AliasThingAPIView
        assert AliasThingAPIView.module_name == "alias_compat_test"
    finally:
        VIEW_REGISTRY.pop("alias_compat_test", None)
