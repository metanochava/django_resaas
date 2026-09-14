"""Configuração declarativa do dashboard 'django_resaas' (visão de
tenancy/plataforma) - só metadados, sem queries (ver
dashboard_providers.py). Mesmos 5 KPIs já mostrados por
pages/django_resaas/DashBoard.vue (Tenancy Dashboard) em quasar_resaas,
agora também disponíveis pelo motor genérico de dashboards."""

from django_resaas.saas import dashboard_providers  # noqa: F401

DASHBOARD = {
    "schema_version": "1.0",

    "name": "django_resaas",
    "label": "Tenancy",
    "icon": "mdi-view-dashboard-outline",
    "route": "dashboard_django_resaas",
    "order": 10,

    "visible": True,

    # Mesma permissão já existente da página antiga (route
    # 'view_django_resaas_dashboard' em router/restRoutes.js) - vista
    # cross-tenant, deliberadamente privilegiada, nunca por omissão.
    "permission": "view_django_resaas_dashboard",

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
            "name": "total_entities",
            "type": "stat",
            "label": "Entities",
            "icon": "mdi-domain",
            "color": "primary",

            "provider": "django_resaas.total_entities",

            "permissions": ["view_django_resaas_dashboard"],
            "permission_mode": "all",

            "visible": True,
            "cols": {"xs": 12, "sm": 6, "md": 4, "lg": 2, "xl": 2},
            "order": 10,

            "accepts_filters": [],
            "filters": [],
        },
        {
            "name": "total_entity_types",
            "type": "stat",
            "label": "Entity Types",
            "icon": "mdi-shape-outline",
            "color": "secondary",

            "provider": "django_resaas.total_entity_types",

            "permissions": ["view_django_resaas_dashboard"],
            "permission_mode": "all",

            "visible": True,
            "cols": {"xs": 12, "sm": 6, "md": 4, "lg": 2, "xl": 2},
            "order": 20,

            "accepts_filters": [],
            "filters": [],
        },
        {
            "name": "total_branches",
            "type": "stat",
            "label": "Branches",
            "icon": "mdi-source-branch",
            "color": "accent",

            "provider": "django_resaas.total_branches",

            "permissions": ["view_django_resaas_dashboard"],
            "permission_mode": "all",

            "visible": True,
            "cols": {"xs": 12, "sm": 6, "md": 4, "lg": 2, "xl": 2},
            "order": 30,

            "accepts_filters": [],
            "filters": [],
        },
        {
            "name": "total_users",
            "type": "stat",
            "label": "Users",
            "icon": "mdi-account-multiple-outline",
            "color": "info",

            "provider": "django_resaas.total_users",

            "permissions": ["view_django_resaas_dashboard"],
            "permission_mode": "all",

            "visible": True,
            "cols": {"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 3},
            "order": 40,

            "accepts_filters": [],
            "filters": [],
        },
        {
            "name": "total_apps",
            "type": "stat",
            "label": "Registered Apps",
            "icon": "mdi-widgets-outline",
            "color": "positive",

            "provider": "django_resaas.total_apps",

            "permissions": ["view_django_resaas_dashboard"],
            "permission_mode": "all",

            "visible": True,
            "cols": {"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 3},
            "order": 50,

            "accepts_filters": [],
            "filters": [],
        },
    ],
}
