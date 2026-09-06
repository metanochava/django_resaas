"""
NotificationsDashboardAPIView - same TenantDashboardAPIView pattern
already used by inventory/sales/saude/hr this session. Confirms the
real nuance found while building it: NotificationRule is TimeModel
(branch is optional, a rule can be "entity-wide") - the default
apply_scope() branch filter would silently drop those, so the view
includes them explicitly instead.
"""
import pytest

from django_resaas.engine.core.tenant.context import ResaasContextService
from django_resaas.engine.models.branch_user_group import BranchUserGroup
from django_resaas.engine.models.group import Group
from django_resaas.notifications.enums import Channel, OutboxStatus
from django_resaas.notifications.models import NotificationDeliveryAttempt, NotificationOutbox
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _create_outbox(tenant, *, status=OutboxStatus.SENT, channel=Channel.EMAIL, event="sales.sale.confirmed", idempotency_key=None):
    return NotificationOutbox.objects.create(
        entity=tenant["entity"],
        branch=tenant["branch"],
        event=event,
        channel=channel,
        category="transactional",
        priority="normal",
        recipient_type="user",
        recipient_identity="user@example.com",
        body="hello",
        status=status,
        idempotency_key=idempotency_key or f"key-{event}-{status}-{channel}",
        created_by=tenant["user"],
        updated_by=tenant["user"],
        state="Active",
    )


def test_dashboard_aggregates_outbox_by_status_and_channel(notification_tenant):
    tenant = notification_tenant

    # A permissão é criada por MODULE_PERMISSIONS (post_migrate) - já
    # existe na base de teste; só falta conceder ao group usado.
    from django.contrib.auth.models import Permission

    perm = Permission.objects.get(codename="view_notifications_dashboard")
    tenant["root_group"].permissions.add(perm)

    _create_outbox(tenant, status=OutboxStatus.SENT, channel=Channel.EMAIL)
    _create_outbox(tenant, status=OutboxStatus.SENT, channel=Channel.SMS)
    failed = _create_outbox(tenant, status=OutboxStatus.FAILED, channel=Channel.EMAIL)
    failed.last_error = "SMTP timeout"
    failed.save(update_fields=["last_error"])

    NotificationDeliveryAttempt.objects.create(
        outbox=failed,
        entity=tenant["entity"],
        branch=tenant["branch"],
        attempt_number=1,
        success=False,
        created_by=tenant["user"],
        updated_by=tenant["user"],
        state="Active",
    )

    response = tenant["client"].get("/api/notifications/dashboard/")
    assert response.status_code == 200, response.data

    assert response.data["total_outbox"] == 3
    by_status = {row["status"]: row["total"] for row in response.data["by_status"]}
    assert by_status["sent"] == 2
    assert by_status["failed"] == 1
    by_channel = {row["channel"]: row["total"] for row in response.data["by_channel"]}
    assert by_channel["email"] == 2
    assert by_channel["sms"] == 1

    assert response.data["total_delivery_attempts"] == 1
    assert response.data["successful_delivery_attempts"] == 0
    assert response.data["delivery_success_rate"] == 0.0

    assert len(response.data["recent_failures"]) == 1
    assert response.data["recent_failures"][0]["last_error"] == "SMTP timeout"


def test_dashboard_includes_entity_wide_rules_in_branch_scope(notification_tenant, make_rule):
    tenant = notification_tenant
    group = Group.objects.get(name="Root")
    from django.contrib.auth.models import Permission

    perm = Permission.objects.get(codename="view_notifications_dashboard")
    group.permissions.add(perm)

    # make_rule já cria com branch=None (entity-wide) - ver conftest.py.
    make_rule(event="sales.sale.confirmed")
    make_rule(event="sales.sale.cancelled", enabled=False)

    response = tenant["client"].get("/api/notifications/dashboard/")
    assert response.status_code == 200, response.data
    assert response.data["total_rules_count"] == 2
    assert response.data["active_rules_count"] == 1


def test_dashboard_requires_permission(notification_tenant):
    """
    "Root" (bootstrap_tenant) é um Group global único (Group.name é
    unique=True) - por isso usamos aqui um Group "Guest" à parte, sem
    nenhuma permissão concedida, tal como o resto desta sessão fez
    repetidamente para testes de "sem permissão".
    """
    tenant = notification_tenant

    guest_group, _ = Group.objects.get_or_create(name="Guest")
    BranchUserGroup.objects.get_or_create(
        user=tenant["user"], branch=tenant["branch"], group=guest_group,
    )
    context = ResaasContextService.issue(
        user=tenant["user"], entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id, group_id=guest_group.id,
    )
    client = APIClient()
    client.force_authenticate(user=tenant["user"])
    client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")

    response = client.get("/api/notifications/dashboard/")
    assert response.status_code == 403
