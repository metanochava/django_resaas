"""Configuração declarativa do dashboard da app 'demo' - só metadados,
sem queries (ver dashboard_providers.py para os providers). Serve como
exemplo mínimo do motor (saas/core/dashboards/) e como fixture real
para os testes de discovery/permissões/filtros do motor."""

from dev.demo import dashboard_providers  # noqa: F401  (regista os providers)

DASHBOARD = {
    "schema_version": "1.0",

    "name": "demo",
    "label": "Demo",
    "icon": "mdi-package-variant",
    "route": "dashboard_demo",
    "order": 999,

    "visible": True,

    # Sem 'permission': qualquer utilizador autenticado com módulo
    # 'demo' activo pode ver o dashboard - política documentada em
    # DashboardPermissionService.can_view_dashboard().
    "permission": None,

    "layout": {
        "columns": 12,
        "gap": "md",
        "dense": False,
    },

    "refresh": {
        "enabled": False,
        "interval": 300,
    },

    "filters": [
        {
            "name": "search",
            "type": "search",
            "label": "Pesquisar",
            "scope": "global",
            "default": None,
        },
    ],

    "widgets": [
        {
            "name": "total_products",
            "type": "stat",
            "label": "Total de produtos",
            "icon": "mdi-package-variant",
            "color": "primary",

            "provider": "demo.total_products",

            "permissions": ["view_product"],
            "permission_mode": "all",

            "visible": True,

            "cols": {"xs": 12},

            "order": 10,

            "accepts_filters": ["search"],
            "filters": [],
        },
        {
            "name": "products_table",
            "type": "table",
            "label": "Produtos",

            "provider": "demo.products_table",

            "permissions": ["view_product"],
            "permission_mode": "all",

            "visible": True,

            "cols": {"xs": 12},

            "order": 20,

            "accepts_filters": ["search"],
            "filters": [],
        },
    ],
}
