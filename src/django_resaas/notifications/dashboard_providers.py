"""Providers dos widgets de notifications/dashboard.py - mesmas
queries já usadas por NotificationsDashboardAPIView (views/dashboard.py,
mecanismo antigo TenantDashboardAPIView), só reorganizadas em widgets
individuais do motor novo (saas/core/dashboards/)."""

from django_resaas.saas.core.dashboards.providers import (
    BaseDashboardProvider,
    register_provider,
)

from django_resaas.notifications.enums import OutboxStatus
from django_resaas.notifications.models import (
    NotificationDeliveryAttempt,
    NotificationOutbox,
    NotificationRule,
)


@register_provider("notifications.total_outbox")
class TotalOutboxProvider(BaseDashboardProvider):

    def resolve(self):
        value = self.scoped_queryset(NotificationOutbox.objects.all()).count()

        return {
            "value": value,
            "formatted_value": str(value),
        }


@register_provider("notifications.delivery_success_rate")
class DeliverySuccessRateProvider(BaseDashboardProvider):

    def resolve(self):
        outbox_qs = self.scoped_queryset(NotificationOutbox.objects.all())
        attempts_qs = NotificationDeliveryAttempt.objects.filter(outbox__in=outbox_qs)

        total = attempts_qs.count()
        successful = attempts_qs.filter(success=True).count()
        rate = round(100 * successful / total, 1) if total else None

        return {
            "value": rate,
            "formatted_value": f"{rate}%" if rate is not None else "-",
        }


@register_provider("notifications.active_rules_count")
class ActiveRulesCountProvider(BaseDashboardProvider):

    def resolve(self):
        # NotificationRule é TimeModel, não BaseModel - branch é opcional
        # (regra pode ser entity-wide, branch=None) - mesma inclusão
        # explícita de entity-wide já feita em views/dashboard.py, só
        # sem o scope=entity (widget sempre no scope branch por omissão
        # aqui, mantendo o provider simples).
        from django.db.models import Q

        rules_qs = NotificationRule.objects.filter(
            entity_id=self.request.entity_id
        ).filter(
            Q(branch_id=self.request.branch_id) | Q(branch__isnull=True)
        )

        value = rules_qs.filter(enabled=True).count()

        return {
            "value": value,
            "formatted_value": str(value),
        }


@register_provider("notifications.recent_failures")
class RecentFailuresProvider(BaseDashboardProvider):

    def resolve(self):
        outbox_qs = self.scoped_queryset(NotificationOutbox.objects.all())

        rows = list(
            outbox_qs
            .filter(status=OutboxStatus.FAILED)
            .order_by("-updated_at")
            .values(
                "id", "event", "channel", "recipient_identity",
                "last_error", "updated_at",
            )[:10]
        )

        return {
            "columns": [
                {"name": "event", "label": "Evento"},
                {"name": "channel", "label": "Canal"},
                {"name": "recipient_identity", "label": "Destinatário"},
                {"name": "last_error", "label": "Erro"},
                {"name": "updated_at", "label": "Actualizado"},
            ],
            "rows": rows,
            "pagination": {
                "count": len(rows),
                "next": False,
                "previous": False,
            },
        }
