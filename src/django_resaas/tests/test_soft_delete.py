"""
FASE 1 - P0.2: soft delete, restore and hard delete, always tenant-scoped.

Uses dev.demo.Product (a plain BaseModel/BaseAPIView resource) through the
real API, so this exercises the actual queryset scoping in
BaseAPIView.get_queryset()/restore()/hard_delete() - not just the ORM
managers in isolation.
"""
import pytest

from dev.demo.models import Product

pytestmark = pytest.mark.django_db


# =========================================================
# DELETE NORMAL (soft)
# =========================================================

def test_soft_delete_preserves_the_tenant(bootstrap_tenant, create_product):
    tenant = bootstrap_tenant("soft-delete-tenant", modules=("demo",))
    product_id = create_product(tenant["client"])

    response = tenant["client"].delete(f"/api/demo/products/{product_id}/")
    assert response.status_code == 204

    # gone from the default (alive-only) manager
    assert not Product.objects.filter(id=product_id).exists()

    # still there via all_objects, correctly marked, tenant untouched
    product = Product.all_objects.get(id=product_id)
    assert product.deleted_at is not None
    assert product.entity_id == tenant["entity"].id
    assert product.branch_id == tenant["branch"].id


def test_retrieve_of_a_soft_deleted_object_is_not_found_by_default(bootstrap_tenant, create_product):
    """
    FASE 3 - P2.12: the plain detail endpoint (no ?objects= at all) must
    behave the same as list - a soft-deleted row is invisible unless the
    caller explicitly asks for it via ?objects=all or ?objects=deleted.
    """
    tenant = bootstrap_tenant("retrieve-deleted-default-tenant", modules=("demo",))
    product_id = create_product(tenant["client"])
    tenant["client"].delete(f"/api/demo/products/{product_id}/")

    response = tenant["client"].get(f"/api/demo/products/{product_id}/")
    assert response.status_code == 404


def test_retrieve_of_a_soft_deleted_object_works_with_objects_all(bootstrap_tenant, create_product):
    tenant = bootstrap_tenant("retrieve-deleted-all-tenant", modules=("demo",))
    product_id = create_product(tenant["client"])
    tenant["client"].delete(f"/api/demo/products/{product_id}/")

    response = tenant["client"].get(f"/api/demo/products/{product_id}/?objects=all")
    assert response.status_code == 200
    assert response.data["id"] == product_id


# =========================================================
# RESTORE
# =========================================================

def test_restore_works_within_the_same_tenant(bootstrap_tenant, create_product):
    tenant = bootstrap_tenant("restore-same-tenant", modules=("demo",))

    product_id = create_product(tenant["client"])
    tenant["client"].delete(f"/api/demo/products/{product_id}/")

    response = tenant["client"].post(f"/api/demo/products/{product_id}/restore/")
    assert response.status_code == 200

    product = Product.objects.get(id=product_id)  # default manager = alive only
    assert product.deleted_at is None


def test_restore_is_blocked_across_tenants(bootstrap_tenant, create_product):
    tenant_a = bootstrap_tenant("restore-tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("restore-tenant-b", modules=("demo",))

    product_id = create_product(tenant_a["client"])
    tenant_a["client"].delete(f"/api/demo/products/{product_id}/")

    response = tenant_b["client"].post(
        f"/api/demo/products/{product_id}/restore/"
    )
    assert response.status_code == 404

    # still soft-deleted - tenant B's blocked attempt changed nothing
    assert Product.all_objects.get(id=product_id).deleted_at is not None


# =========================================================
# HARD DELETE
# =========================================================

def test_hard_delete_permanently_removes_the_row(bootstrap_tenant, create_product):
    tenant = bootstrap_tenant("hard-delete-tenant", modules=("demo",))
    product_id = create_product(tenant["client"])

    response = tenant["client"].delete(f"/api/demo/products/{product_id}/")
    assert response.status_code == 204

    response = tenant["client"].delete(
        f"/api/demo/products/{product_id}/hard_delete/"
    )
    assert response.status_code == 200

    # gone even from all_objects (soft-deleted rows would still show up there)
    assert not Product.all_objects.filter(id=product_id).exists()


def test_hard_delete_is_blocked_across_tenants(bootstrap_tenant, create_product):
    tenant_a = bootstrap_tenant("hard-delete-cross-tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("hard-delete-cross-tenant-b", modules=("demo",))

    product_id = create_product(tenant_a["client"])
    tenant_a["client"].delete(f"/api/demo/products/{product_id}/")

    response = tenant_b["client"].delete(
        f"/api/demo/products/{product_id}/hard_delete/"
    )
    assert response.status_code == 404

    # untouched - still there (soft-deleted) for tenant A
    assert Product.all_objects.filter(id=product_id).exists()


# =========================================================
# ?objects=all
# =========================================================

def test_objects_all_remains_tenant_scoped(bootstrap_tenant, create_product):
    tenant_a = bootstrap_tenant("all-scope-tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("all-scope-tenant-b", modules=("demo",))

    product_id = create_product(tenant_a["client"])
    tenant_a["client"].delete(f"/api/demo/products/{product_id}/")

    # tenant B must see nothing, even when asking for "all" objects
    response = tenant_b["client"].get("/api/demo/products/?objects=all")
    assert response.data["count"] == 0

    # tenant A does see its own soft-deleted row via "all" (active + deleted)
    response = tenant_a["client"].get("/api/demo/products/?objects=all")
    assert response.data["count"] == 1


# =========================================================
# ?objects=deleted
# =========================================================

def test_deleted_query_remains_tenant_scoped(bootstrap_tenant, create_product):
    tenant_a = bootstrap_tenant("deleted-scope-tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("deleted-scope-tenant-b", modules=("demo",))

    product_id = create_product(tenant_a["client"])
    tenant_a["client"].delete(f"/api/demo/products/{product_id}/")

    # tenant B must not see tenant A's soft-deleted row
    response = tenant_b["client"].get("/api/demo/products/?objects=deleted")
    assert response.data["count"] == 0

    # tenant A does see its own soft-deleted row
    response = tenant_a["client"].get("/api/demo/products/?objects=deleted")
    assert response.data["count"] == 1
