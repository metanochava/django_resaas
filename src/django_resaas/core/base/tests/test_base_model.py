"""
BaseModel must never guess a tenant. Before this test existed,
`BaseModel.ensure_tenant()` silently fell back to `Entity.objects.first()`
/ `Branch.objects.first()` when entity/branch were missing on save - which
in a multi-tenant system means data can end up attached to the wrong
tenant without anyone noticing. These tests lock in the replacement
behavior: saving without an explicit entity *and* branch always raises,
with no automatic selection of any kind.
"""
import pytest
from django.core.exceptions import ValidationError

from dev.demo.models import Product

pytestmark = pytest.mark.django_db


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
