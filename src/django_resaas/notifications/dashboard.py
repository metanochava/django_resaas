"""Configuração declarativa do dashboard da app 'notifications' - só
metadados, sem queries (ver dashboard_providers.py). Mesmas métricas já
expostas pelo mecanismo antigo (views/dashboard.py's
NotificationsDashboardAPIView), reorganizadas como widgets do motor
novo (saas/core/dashboards/)."""

from django_resaas.notifications import dashboard_providers  # noqa: F401

DASHBOARD = {
    "schema_version": "1.0",

    "name": "notifications",
    "label": "Notifications",
    "icon": "mdi-bell-outline",
    "route": "dashboard_notifications",
    "order": 30,

    "visible": True,

    # Mesma permissão já existente do mecanismo antigo
    # (NotificationsDashboardAPIView.permission_codename).
    "permission": "view_notifications_dashboard",

    "layout": {
        "columns": 12,
        "gap": "md",
        "dense": False,
    },

    "refresh": {
        "enabled": False,
        "interval": 300,
    },

    "filters": [],

    "widgets": [
        {
            "name": "total_outbox",
            "type": "stat",
            "label": "Total na Outbox",
            "icon": "mdi-tray-full",
            "color": "primary",

            "provider": "notifications.total_outbox",

            "permissions": ["view_notifications_dashboard"],
            "permission_mode": "all",

            "visible": True,
            "cols": {"xs": 12, "sm": 6, "md": 4, "lg": 4, "xl": 4},
            "order": 10,

            "accepts_filters": [],
            "filters": [],
        },
        {
            "name": "delivery_success_rate",
            "type": "stat",
            "label": "Taxa de entrega",
            "icon": "mdi-check-circle-outline",
            "color": "positive",
            "suffix": "%",

            "provider": "notifications.delivery_success_rate",

            "permissions": ["view_notifications_dashboard"],
            "permission_mode": "all",

            "visible": True,
            "cols": {"xs": 12, "sm": 6, "md": 4, "lg": 4, "xl": 4},
            "order": 20,

            "accepts_filters": [],
            "filters": [],
        },
        {
            "name": "active_rules_count",
            "type": "stat",
            "label": "Regras activas",
            "icon": "mdi-cog-outline",
            "color": "secondary",

            "provider": "notifications.active_rules_count",

            "permissions": ["view_notifications_dashboard"],
            "permission_mode": "all",

            "visible": True,
            "cols": {"xs": 12, "sm": 6, "md": 4, "lg": 4, "xl": 4},
            "order": 30,

            "accepts_filters": [],
            "filters": [],
        },
        {
            "name": "recent_failures",
            "type": "table",
            "label": "Falhas recentes",

            "provider": "notifications.recent_failures",

            "permissions": ["view_notifications_dashboard"],
            "permission_mode": "all",

            "visible": True,
            "cols": {"xs": 12},
            "order": 40,

            "accepts_filters": [],
            "filters": [],
        },
    ],
}
