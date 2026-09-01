"""
FASE 1 - P0.1: tenant is always explicit, never guessed.

BaseModel.ensure_tenant() used to silently fall back to
`Entity.objects.first()` / `Branch.objects.first()` when entity/branch
were missing on save - in a multi-tenant system that means data can end
up attached to the wrong tenant without anyone noticing. It now raises
instead. These tests lock that in, and separately prove isolation is
enforced end-to-end through the real API (BaseAPIView), both across
entities and across branches of the SAME entity.
"""
import pytest
from django.core.exceptions import ValidationError

from dev.demo.models import Product

pytestmark = pytest.mark.django_db


# =========================================================
# TENANT OBRIGATÓRIO (ensure_tenant)
# =========================================================

def test_save_without_entity_or_branch_raises():
    product = Product(name="No Tenant", sku="X", price="1.00")

    with pytest.raises(ValidationError):
        product.save()

    assert not Product.all_objects.filter(sku="X").exists()


def test_save_with_entity_but_no_branch_raises(bootstrap_tenant):
    tenant = bootstrap_tenant("partial-tenant-entity-only")

    product = Product(
        name="Half Tenant", sku="Y", price="1.00", entity=tenant["entity"]
    )

    with pytest.raises(ValidationError):
        product.save()

    assert not Product.all_objects.filter(sku="Y").exists()


def test_save_with_branch_but_no_entity_raises(bootstrap_tenant):
    tenant = bootstrap_tenant("partial-tenant-branch-only")

    product = Product(
        name="Half Tenant", sku="Z", price="1.00", branch=tenant["branch"]
    )

    with pytest.raises(ValidationError):
        product.save()

    assert not Product.all_objects.filter(sku="Z").exists()


def test_never_borrows_another_tenants_branch(bootstrap_tenant):
    """
    Regression guard for the specific danger of the old fallback: giving
    only `entity` (no `branch`) must never silently attach a branch
    belonging to some other, unrelated tenant - or any branch at all.
    """
    tenant_a = bootstrap_tenant("branch-fallback-tenant-a")
    bootstrap_tenant("branch-fallback-tenant-b")  # just needs to exist

    product = Product(
        name="X", sku="NO-BRANCH", price="1.00", entity=tenant_a["entity"]
    )

    with pytest.raises(ValidationError):
        product.save()

    assert not Product.all_objects.filter(sku="NO-BRANCH").exists()


def test_save_with_explicit_entity_and_branch_succeeds(bootstrap_tenant):
    tenant = bootstrap_tenant("explicit-tenant")

    product = Product(
        name="Explicit",
        sku="OK-1",
        price="1.00",
        entity=tenant["entity"],
        branch=tenant["branch"],
    )
    product.save()

    assert product.entity_id == tenant["entity"].id
    assert product.branch_id == tenant["branch"].id


# =========================================================
# ISOLAMENTO POR ENTIDADE (via API real / BaseAPIView)
# =========================================================

def test_entity_a_cannot_list_entity_b_records(bootstrap_tenant, create_product):
    tenant_a = bootstrap_tenant("entity-list-a", modules=("demo",))
    tenant_b = bootstrap_tenant("entity-list-b", modules=("demo",))

    create_product(tenant_a["client"], name="A's Widget")

    response = tenant_b["client"].get("/api/demo/products/")
    assert response.data["count"] == 0

    # confirmed at the DB level too: both scoped to different entities
    assert Product.objects.filter(entity=tenant_a["entity"]).count() == 1
    assert Product.objects.filter(entity=tenant_b["entity"]).count() == 0


def test_entity_a_cannot_retrieve_entity_bs_record(bootstrap_tenant, create_product):
    tenant_a = bootstrap_tenant("entity-retrieve-a", modules=("demo",))
    tenant_b = bootstrap_tenant("entity-retrieve-b", modules=("demo",))

    product_id = create_product(tenant_a["client"], name="A's Widget")

    response = tenant_b["client"].get(f"/api/demo/products/{product_id}/")
    assert response.status_code == 404

    # tenant A can retrieve its own record just fine
    response = tenant_a["client"].get(f"/api/demo/products/{product_id}/")
    assert response.status_code == 200


# =========================================================
# ISOLAMENTO POR BRANCH (mesma entidade)
# =========================================================

def test_branch_isolation_is_enforced(bootstrap_tenant, create_product):
    """
    Two branches under the SAME entity - not just two different entities -
    must not see each other's data either. Grants the same user access to
    a second branch (mirroring what onboarding a user into a new branch
    actually does) and issues a second signed context for it.
    """
    from django_resaas.core.tenant.context import ResaasContextService
    from django_resaas.models.branch import Branch
    from django_resaas.models.branch_user_group import BranchUserGroup
    from rest_framework.test import APIClient

    tenant = bootstrap_tenant("branch-isolation-tenant", modules=("demo",))

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

    response = client_b.get("/api/demo/products/")
    assert response.data["count"] == 0

    assert Product.objects.filter(branch=tenant["branch"]).count() == 1
    assert Product.objects.filter(branch=branch_b).count() == 0
