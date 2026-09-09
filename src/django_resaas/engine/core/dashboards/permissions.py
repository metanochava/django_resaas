"""Autorização do motor de dashboards - reutiliza exactamente o motor
de permissões já existente (isPermited/check_permission,
engine/core/base/permissions.py) e a verificação de módulo activo já
existente (is_module_active, engine/core/base/dashboard.py, extraída
de TenantDashboardAPIView).

Política de "sem permissão declarada" (dashboard ou widget): qualquer
utilizador autenticado que já tenha contexto de tenant válido e módulo
activo pode ver - mesma política que o próprio prompt definiu
explicitamente para widgets sem 'permissions', aplicada aqui também ao
dashboard sem 'permission'. Documentado, não é omissão.
"""

from django_resaas.engine.core.base.dashboard import is_module_active
from django_resaas.engine.core.base.permissions import isPermited
from django_resaas.engine.core.dashboards.exceptions import DashboardPermissionError


class DashboardPermissionService:

    @staticmethod
    def ensure_module_active(request, dashboard_config):
        module_name = dashboard_config["name"]

        if not is_module_active(request.entity_id, module_name):
            raise DashboardPermissionError(
                f"Module '{module_name}' is not active.",
                code="module_not_active",
            )

    @staticmethod
    def can_view_dashboard(request, dashboard_config):
        permission = dashboard_config.get("permission")

        if not permission:
            return True

        return isPermited(request=request, role=permission)

    @staticmethod
    def ensure_dashboard_authorized(request, dashboard_config):
        DashboardPermissionService.ensure_module_active(request, dashboard_config)

        if not DashboardPermissionService.can_view_dashboard(request, dashboard_config):
            raise DashboardPermissionError("Unauthorized")

    @staticmethod
    def can_view_widget(request, widget_config):
        permissions = widget_config.get("permissions") or []

        if not permissions:
            return True

        mode = widget_config.get("permission_mode", "any")

        checks = (
            isPermited(request=request, role=codename)
            for codename in permissions
        )

        if mode == "all":
            return all(checks)

        return any(checks)

    @staticmethod
    def filter_authorized_widgets(request, dashboard_config):
        """Devolve só os widgets que o utilizador pode ver - nunca
        widgets escondidos-mas-presentes no payload (ver secção
        "Protecção de endpoints" do pedido: esconder no frontend não é
        segurança, o backend não devolve o que não é autorizado)."""

        return [
            widget
            for widget in dashboard_config.get("widgets", [])
            if widget.get("visible", True)
            and DashboardPermissionService.can_view_widget(request, widget)
        ]

    @staticmethod
    def get_widget_or_raise(request, dashboard_config, widget_name):
        widget = next(
            (
                w for w in dashboard_config.get("widgets", [])
                if w["name"] == widget_name
            ),
            None,
        )

        if widget is None:
            raise DashboardPermissionError(
                f"Widget '{widget_name}' not found.",
                code="widget_not_found",
                status_code=404,
            )

        if not widget.get("visible", True) or not DashboardPermissionService.can_view_widget(
            request, widget
        ):
            # 403, nunca 404 - 404 revelaria a um utilizador sem
            # permissão se o widget existe ou não; mas também nunca
            # dados vazios silenciosos (ver pedido: "deve receber HTTP
            # 403 e não dados vazios que escondam falha de
            # autorização").
            raise DashboardPermissionError("Unauthorized")

        return widget
