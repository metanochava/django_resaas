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
    from django_resaas.engine.core.tenant.context import ResaasContextService
    from django_resaas.engine.models.group import Group

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
    assert response.status_code == 400
    assert response.data["detail"] == "Unauthorized"


def test_register_view_and_registerView_are_the_same_decorator():
    """registerView (camelCase) is the original name every existing
    @registerView(...) call site uses; register_view is the PEP 8-consistent
    alias for new code - they must be the exact same object."""
    from django_resaas.engine.core.base.views import register_view, registerView

    assert registerView is register_view
