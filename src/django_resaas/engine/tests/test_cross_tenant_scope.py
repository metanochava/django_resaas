"""
Phase 0 of the Patient-longitudinal/Health/Pharmacy initiative (see
back/docs/architecture/patient-longitudinal-health-pharmacy.md) - the
`cross_branch_actions`/`cross_entity_actions` opt-in described in
CLAUDE.md section 10.

BaseAPIView.get_queryset() used to filter by entity_id/branch_id
unconditionally whenever the model had those fields, with no way for a
view to declare that a specific action is allowed to look beyond the
current Branch/Entity (e.g. a future longitudinal Patient search). This
adds that opt-in, defaulting to `[]` on both lists so existing behaviour
is unchanged unless a view explicitly opts an action in - see
test_tenant.py for the pre-existing default-isolation coverage this
must not regress.
"""
import pytest

from dev.demo.models import Product
from dev.demo.views import ProductAPIView

pytestmark = pytest.mark.django_db


def test_defaults_are_empty_and_isolation_is_unchanged():
    assert ProductAPIView.cross_branch_actions == []
    assert ProductAPIView.cross_entity_actions == []


def test_opting_a_action_into_cross_branch_exposes_other_branches(
    bootstrap_tenant, create_product, monkeypatch
):
    from django_resaas.engine.core.tenant.context import ResaasContextService
    from django_resaas.engine.models.branch import Branch
    from django_resaas.engine.models.branch_user_group import BranchUserGroup
    from rest_framework.test import APIClient

    monkeypatch.setattr(ProductAPIView, "cross_branch_actions", ["list"])

    tenant = bootstrap_tenant("cross-branch-tenant", modules=("demo",))
    branch_b = Branch.objects.create(name="Branch B", entity=tenant["entity"])
    BranchUserGroup.objects.get_or_create(
        user=tenant["user"],
        branch=branch_b,
        group=tenant["root_group"],
        defaults={"state": 1},
    )

    create_product(tenant["client"], name="Branch A's Widget")

    context_b = ResaasContextService.issue(
        user=tenant["user"],
        entity_id=tenant["entity"].id,
        branch_id=branch_b.id,
        group_id=tenant["root_group"].id,
    )
    client_b = APIClient()
    client_b.force_authenticate(user=tenant["user"])
    client_b.credentials(HTTP_X_RESAAS_CONTEXT=context_b["token"], HTTP_L="1")

    # "list" is opted in: branch B now sees branch A's record too.
    response = client_b.get("/api/demo/products/")
    assert response.data["count"] == 1

    # "retrieve" was NOT opted in: the per-action opt-in doesn't leak
    # to other actions on the same view.
    product_id = Product.objects.get(branch=tenant["branch"]).id
    response = client_b.get(f"/api/demo/products/{product_id}/")
    assert response.status_code == 404


def test_opting_a_action_into_cross_entity_exposes_other_entities(
    bootstrap_tenant, create_product, monkeypatch
):
    monkeypatch.setattr(ProductAPIView, "cross_entity_actions", ["list"])

    tenant_a = bootstrap_tenant("cross-entity-tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("cross-entity-tenant-b", modules=("demo",))

    create_product(tenant_a["client"], name="A's Widget")

    # "list" is opted in: entity B now sees entity A's record too.
    response = tenant_b["client"].get("/api/demo/products/")
    assert response.data["count"] == 1

    # "retrieve" was NOT opted in.
    product_id = Product.objects.get(entity=tenant_a["entity"]).id
    response = tenant_b["client"].get(f"/api/demo/products/{product_id}/")
    assert response.status_code == 404


def test_cross_entity_action_implicitly_crosses_branch_too(
    bootstrap_tenant, create_product, monkeypatch
):
    """A cross-entity operation inherently spans branches (CLAUDE.md
    section 10) - opting an action into cross_entity_actions alone,
    with cross_branch_actions left empty, must still skip branch
    filtering for that action."""
    monkeypatch.setattr(ProductAPIView, "cross_entity_actions", ["list"])
    assert ProductAPIView.cross_branch_actions == []

    tenant_a = bootstrap_tenant("cross-entity-branch-a", modules=("demo",))
    tenant_b = bootstrap_tenant("cross-entity-branch-b", modules=("demo",))

    create_product(tenant_a["client"], name="A's Widget")

    response = tenant_b["client"].get("/api/demo/products/")
    assert response.data["count"] == 1


def test_scope_opt_in_does_not_grant_permission(bootstrap_tenant, monkeypatch):
    """Scope says where data may come from; permission says whether the
    user may perform the operation - both must pass (CLAUDE.md section
    10). Opting "list" into cross_entity_actions must not let a user
    without list permission through."""
    from django_resaas.engine.models.group import Group

    monkeypatch.setattr(ProductAPIView, "cross_entity_actions", ["list"])

    tenant = bootstrap_tenant("cross-entity-no-perm", modules=("demo",))
    guest_group = Group.objects.get(name="Guest")
    from django_resaas.engine.core.tenant.context import ResaasContextService

    context = ResaasContextService.issue(
        user=tenant["user"],
        entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id,
        group_id=guest_group.id,
    )
    tenant["client"].credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")

    response = tenant["client"].get("/api/demo/products/")
    assert response.status_code == 400
    assert response.data["detail"] == "Unauthorized"
