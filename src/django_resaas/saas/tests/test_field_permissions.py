"""
Field-level authorization (saas/core/base/field_access.py), exercised on the
dev demo's Agreement.amount: view_agreement gives the agreement,
view_agreement_amount / change_agreement_amount give the amount. (An
application's hr module runs the same checks on Contract.salary.)
"""
from datetime import date
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Permission

from django_resaas.saas.models.person import Person
from dev.demo.models import Agreement, Member
from dev.demo.serializers import AgreementSerializer
from dev.demo.views import AgreementAPIView

pytestmark = pytest.mark.django_db

URL = "/api/demo/agreements/"


def _tenant(bootstrap_tenant, name):
    return bootstrap_tenant(name, modules=("demo",))


def _make_member(tenant, code="MEM-FP-1"):
    person = Person.objects.create(name="Field", surname="Perm")
    return Member.objects.create(
        entity=tenant["entity"], branch=tenant["branch"], person=person,
        code=code, joined_on=date(2024, 1, 1),
    )


def _make_agreement(tenant, member, amount, start_date=date(2025, 1, 1), number=None):
    return Agreement.objects.create(
        entity=tenant["entity"], branch=tenant["branch"], member=member,
        start_date=start_date, amount=amount, number=number,
    )


def _revoke(tenant, *codenames):
    tenant["root_group"].permissions.remove(*Permission.objects.filter(codename__in=codenames))


def _results(response):
    data = response.json()
    return data["results"] if isinstance(data, dict) and "results" in data else data


# =============================================================
# PERMISSION SYNC + SCHEMA
# =============================================================

def test_field_permissions_are_synced_and_root_holds_them(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-sync")

    codenames = set(
        tenant["root_group"].permissions
        .filter(codename__in=["view_agreement_amount", "change_agreement_amount"])
        .values_list("codename", flat=True)
    )
    assert codenames == {"view_agreement_amount", "change_agreement_amount"}


def test_schema_describes_the_field_permissions():
    from django_resaas.saas.management.apicommands.view.app_schema import _schema_fields

    fields = {f["name"]: f for f in _schema_fields(Agreement)}

    assert fields["amount"]["permissions"] == {
        "view": "view_agreement_amount",
        "change": "change_agreement_amount",
    }
    assert "permissions" not in fields["start_date"]


# =============================================================
# READ
# =============================================================

def test_with_permissions_the_amount_is_returned(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-read-ok")
    agreement = _make_agreement(tenant, _make_member(tenant), "1500.00")

    response = tenant["client"].get(f"{URL}{agreement.id}/")

    assert response.status_code == 200
    assert response.json()["amount"] == "1500.00"


def test_without_view_permission_the_amount_is_hidden_in_retrieve_and_list(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-read-denied")
    agreement = _make_agreement(tenant, _make_member(tenant), "1500.00")
    _revoke(tenant, "view_agreement_amount", "change_agreement_amount")

    detail = tenant["client"].get(f"{URL}{agreement.id}/")
    listing = tenant["client"].get(URL)

    assert detail.status_code == 200
    assert "amount" not in detail.json()
    assert detail.json()["id"] == str(agreement.id)

    assert listing.status_code == 200
    rows = _results(listing)
    assert rows and all("amount" not in row for row in rows)


def test_serializer_without_request_hides_the_amount(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-no-request")
    agreement = _make_agreement(tenant, _make_member(tenant), "1500.00")

    assert "amount" not in AgreementSerializer(agreement).data


# =============================================================
# FILTER / ORDERING / PDF - no side channel
# =============================================================

def test_without_view_permission_the_amount_filter_is_ignored(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-filter")
    member = _make_member(tenant)
    _make_agreement(tenant, member, "1000.00", number="C-1")
    _make_agreement(tenant, member, "2000.00", number="C-2")

    allowed = tenant["client"].get(URL, {"amount": "1000.00"})
    assert len(_results(allowed)) == 1

    _revoke(tenant, "view_agreement_amount", "change_agreement_amount")

    denied = tenant["client"].get(URL, {"amount": "1000.00"})
    assert denied.status_code == 200
    assert len(_results(denied)) == 2


def test_without_view_permission_the_amount_ordering_is_ignored(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-ordering")
    member = _make_member(tenant)
    # default ordering is -start_date: C-LOW first; ordering by amount would put C-HIGH first
    _make_agreement(tenant, member, "1000.00", start_date=date(2025, 6, 1), number="C-LOW")
    _make_agreement(tenant, member, "9000.00", start_date=date(2025, 1, 1), number="C-HIGH")

    allowed = tenant["client"].get(URL, {"ordering": "-amount"})
    assert [r["number"] for r in _results(allowed)] == ["C-HIGH", "C-LOW"]

    _revoke(tenant, "view_agreement_amount", "change_agreement_amount")

    denied = tenant["client"].get(URL, {"ordering": "-amount"})
    assert denied.status_code == 200
    assert [r["number"] for r in _results(denied)] == ["C-LOW", "C-HIGH"]


def test_pdf_fields_hide_the_amount_without_view_permission(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-pdf")
    agreement = _make_agreement(tenant, _make_member(tenant), "1500.00")
    view = AgreementAPIView()

    def labels(allowed):
        request = SimpleNamespace(lang_id=None, _perm_cache={"view_agreement_amount": allowed})
        return [f["label"] for f in view.get_pdf_fields(request, agreement)]

    assert "Amount" in labels(True)
    assert "Amount" not in labels(False)


# =============================================================
# WRITE
# =============================================================

def test_with_permissions_an_agreement_is_created_with_its_amount(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-create-ok")
    member = _make_member(tenant)

    response = tenant["client"].post(URL, {
        "member": str(member.id), "start_date": "2025-01-01", "amount": "1200.00",
    }, format="json")

    assert response.status_code == 201, response.json()
    assert response.json()["amount"] == "1200.00"


def test_without_change_permission_sending_the_amount_is_forbidden(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-create-denied")
    member = _make_member(tenant)
    _revoke(tenant, "change_agreement_amount")

    response = tenant["client"].post(URL, {
        "member": str(member.id), "start_date": "2025-01-01", "amount": "1200.00",
    }, format="json")

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "field_permission_denied"
    assert error["details"] == {"fields": ["amount"]}
    assert not Agreement.objects.filter(member=member).exists()


def test_without_change_permission_create_cannot_omit_the_required_amount(bootstrap_tenant):
    """amount is required on the model: a caller who may not set it cannot
    create an agreement at all - 403, never a 500 from the database."""
    tenant = _tenant(bootstrap_tenant, "fp-create-missing")
    member = _make_member(tenant)
    _revoke(tenant, "change_agreement_amount")

    response = tenant["client"].post(URL, {
        "member": str(member.id), "start_date": "2025-01-01",
    }, format="json")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "field_permission_denied"


def test_view_only_can_read_the_amount_but_not_patch_it(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-view-only")
    agreement = _make_agreement(tenant, _make_member(tenant), "1500.00")
    _revoke(tenant, "change_agreement_amount")

    assert tenant["client"].get(f"{URL}{agreement.id}/").json()["amount"] == "1500.00"

    response = tenant["client"].patch(f"{URL}{agreement.id}/", {"amount": "9999.00"}, format="json")

    assert response.status_code == 403
    agreement.refresh_from_db()
    assert str(agreement.amount) == "1500.00"


def test_without_amount_permissions_other_fields_can_still_be_patched(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-patch-other")
    agreement = _make_agreement(tenant, _make_member(tenant), "1500.00")
    _revoke(tenant, "view_agreement_amount", "change_agreement_amount")

    response = tenant["client"].patch(f"{URL}{agreement.id}/", {"number": "C-NEW"}, format="json")

    assert response.status_code == 200, response.json()
    assert "amount" not in response.json()
    agreement.refresh_from_db()
    assert agreement.number == "C-NEW"
    assert str(agreement.amount) == "1500.00"


def test_change_without_view_writes_the_amount_but_never_returns_it(bootstrap_tenant):
    tenant = _tenant(bootstrap_tenant, "fp-write-only")
    agreement = _make_agreement(tenant, _make_member(tenant), "1500.00")
    _revoke(tenant, "view_agreement_amount")

    response = tenant["client"].patch(f"{URL}{agreement.id}/", {"amount": "1700.00"}, format="json")

    assert response.status_code == 200, response.json()
    assert "amount" not in response.json()
    agreement.refresh_from_db()
    assert str(agreement.amount) == "1700.00"


def test_view_only_whole_form_patch_resending_the_same_amount_is_accepted(bootstrap_tenant):
    """BaseStore PATCHes the whole loaded record back - re-sending the amount
    the agreement already holds is not a change."""
    tenant = _tenant(bootstrap_tenant, "fp-same-value")
    agreement = _make_agreement(tenant, _make_member(tenant), "1500.00")
    _revoke(tenant, "change_agreement_amount")

    response = tenant["client"].patch(
        f"{URL}{agreement.id}/", {"amount": "1500.00", "number": "C-EDIT"}, format="json"
    )

    assert response.status_code == 200, response.json()
    agreement.refresh_from_db()
    assert agreement.number == "C-EDIT"
    assert str(agreement.amount) == "1500.00"
