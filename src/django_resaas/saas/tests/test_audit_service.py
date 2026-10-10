"""audit_service.record: one place that writes AuditLog rows, with optional
structured details (AuditLog.details)."""
import pytest

from django_resaas.saas.core.services import audit_service
from django_resaas.saas.models.audit_log import AuditLog

pytestmark = pytest.mark.django_db


def test_details_are_stored_with_the_event(bootstrap_tenant):
    tenant = bootstrap_tenant("audit-details")

    row = audit_service.record(action="SAMPLE_REJECTED", target=tenant["user"], actor=tenant["user"],
                               entity_id=tenant["entity"].id,
                               details={"reason": "Haemolysed", "from": "colhido", "to": "recolha_necessaria"})

    row.refresh_from_db()
    assert row.details == {"reason": "Haemolysed", "from": "colhido", "to": "recolha_necessaria"}
    assert row.entity_id == tenant["entity"].id


def test_details_are_optional(bootstrap_tenant):
    tenant = bootstrap_tenant("audit-plain")

    row = audit_service.record(action="SOMETHING", target=tenant["user"], actor=tenant["user"])

    assert AuditLog.objects.get(pk=row.pk).details is None
