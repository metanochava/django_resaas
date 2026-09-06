from django.db.models import Count, Q

from rest_framework.response import Response

from django_resaas.engine.core.base.dashboard import TenantDashboardAPIView
from django_resaas.engine.core.base.views import register_view

from django_resaas.notifications.enums import OutboxStatus
from django_resaas.notifications.models import (
    NotificationDeliveryAttempt,
    NotificationOutbox,
    NotificationRule,
)


@register_view("dashboard", module="notifications")
class NotificationsDashboardAPIView(TenantDashboardAPIView):
    """
    Visão geral do módulo Notifications: estado da Outbox, taxa de
    sucesso de entrega, regras activas, e falhas recentes. Mesmo
    padrão (TenantDashboardAPIView) já usado por inventory/sales/
    saude/hr - ver docs/architecture/patient-longitudinal-health-pharmacy.md
    para o histórico desta convenção.
    """

    module_name = "notifications"
    permission_codename = "view_notifications_dashboard"

    def get(self, request, *args, **kwargs):
        outbox_qs = self.apply_scope(request, NotificationOutbox.objects.all())
        attempts_qs = NotificationDeliveryAttempt.objects.filter(
            outbox__in=outbox_qs
        )

        # NotificationRule é TimeModel, não BaseModel - branch é opcional
        # (uma regra pode ser "entity-wide", branch=None). apply_scope()
        # filtra por branch_id exacto, o que excluiria essas regras
        # entity-wide do scope "branch" (default) - aqui incluímos
        # explicitamente as duas: as desta branch e as entity-wide.
        rules_qs = NotificationRule.objects.filter(entity_id=request.entity_id)

        if request.query_params.get("scope") != "entity":
            rules_qs = rules_qs.filter(
                Q(branch_id=request.branch_id) | Q(branch__isnull=True)
            )

        by_status = (
            outbox_qs
            .values("status")
            .annotate(total=Count("id"))
            .order_by("status")
        )

        by_channel = (
            outbox_qs
            .values("channel")
            .annotate(total=Count("id"))
            .order_by("channel")
        )

        total_attempts = attempts_qs.count()
        successful_attempts = attempts_qs.filter(success=True).count()
        success_rate = (
            round(100 * successful_attempts / total_attempts, 1)
            if total_attempts
            else None
        )

        recent_failures = list(
            outbox_qs
            .filter(status=OutboxStatus.FAILED)
            .order_by("-updated_at")[:10]
            .values(
                "id", "event", "channel", "recipient_identity",
                "last_error", "updated_at",
            )
        )

        return Response({
            "total_outbox": outbox_qs.count(),
            "by_status": list(by_status),
            "by_channel": list(by_channel),
            "total_delivery_attempts": total_attempts,
            "successful_delivery_attempts": successful_attempts,
            "delivery_success_rate": success_rate,
            "active_rules_count": rules_qs.filter(enabled=True).count(),
            "total_rules_count": rules_qs.count(),
            "recent_failures": recent_failures,
        })
