"""Endpoints genéricos do motor de dashboards.

Um único conjunto de 4 endpoints serve QUALQUER dashboard declarado em
`<app>/dashboard.py` - o backend resolve app_name/widget_name via
DashboardRegistry + DashboardProviderRegistry, replicando o fluxo
completo pedido:

    request -> tenant -> dashboard permission -> module active ->
    widget permission -> filter validation -> provider -> resposta

Registados directamente em django_resaas/urls.py (com path
converters `<str:app_name>`/`<str:widget_name>`/`<str:filter_name>`),
não via @register_view/VIEW_REGISTRY - build_saas_urls() só gera
prefixos estáticos `{module}/{name}/`, sem parâmetros de path (ver
engine/core/utils/autoload_urls.py).
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from django_resaas.engine.core.dashboards.discovery import DashboardDiscoveryService
from django_resaas.engine.core.dashboards.exceptions import (
    DashboardEngineError,
    DashboardNotFoundError,
)
from django_resaas.engine.core.dashboards.filters import DashboardFilterService
from django_resaas.engine.core.dashboards.permissions import DashboardPermissionService
from django_resaas.engine.core.dashboards.providers import resolve_provider
from django_resaas.engine.core.dashboards.registry import DashboardRegistry
from django_resaas.engine.core.dashboards.response import DashboardResponseService


class _DashboardEngineAPIView(APIView):
    """Mesma validação de tenant que TenantDashboardAPIView.initial()
    (contexto obrigatório, entity obrigatória) - mas sem exigir um
    único `module_name`/`permission_codename` fixos, porque estes
    endpoints são genéricos e resolvem o módulo a partir do path
    (`app_name`)."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if getattr(request, "tenant_context_error", None):
            raise PermissionDenied(str(request.tenant_context_error))

        if not getattr(request, "tenant_context", None):
            raise PermissionDenied("RESAAS context is required.")

        DashboardDiscoveryService.discover()

    def handle_exception(self, exc):
        if isinstance(exc, DashboardEngineError):
            payload, status_code = DashboardResponseService.error_response(exc)
            return Response(payload, status=status_code)

        return super().handle_exception(exc)

    def _get_dashboard_or_404(self, app_name):
        dashboard = DashboardRegistry.get(app_name)

        if dashboard is None:
            raise DashboardNotFoundError(f"Dashboard '{app_name}' not found.")

        return dashboard


class DashboardListAPIView(_DashboardEngineAPIView):
    """GET /api/django_resaas/dashboards/ - lista leve (sem widgets)
    dos dashboards autorizados para o utilizador/tenant actual."""

    def get(self, request, *args, **kwargs):
        summaries = []

        for dashboard in DashboardRegistry.get_all():
            if not dashboard.get("visible", True):
                continue

            try:
                DashboardPermissionService.ensure_dashboard_authorized(request, dashboard)
            except DashboardEngineError:
                continue

            summaries.append({
                "name": dashboard["name"],
                "label": dashboard["label"],
                "icon": dashboard.get("icon"),
                "route": dashboard.get("route"),
                "order": dashboard.get("order", 999),
            })

        return Response(summaries)


class DashboardDetailAPIView(_DashboardEngineAPIView):
    """GET /api/django_resaas/dashboard/<app_name>/ - configuração
    completa e já filtrada (só widgets autorizados) de um dashboard."""

    def get(self, request, app_name, *args, **kwargs):
        dashboard = self._get_dashboard_or_404(app_name)

        DashboardPermissionService.ensure_dashboard_authorized(request, dashboard)

        dashboard["widgets"] = DashboardPermissionService.filter_authorized_widgets(
            request, dashboard
        )

        return Response({"dashboard": dashboard})


class DashboardWidgetDataAPIView(_DashboardEngineAPIView):
    """GET /api/django_resaas/dashboard/<app_name>/widget/<widget_name>/

    Protegido de forma independente do endpoint de detalhe - um
    pedido directo a este URL sem autorização recebe 403, nunca dados
    vazios (a segurança nunca depende de o frontend "não mostrar" o
    widget)."""

    def get(self, request, app_name, widget_name, *args, **kwargs):
        dashboard = self._get_dashboard_or_404(app_name)

        DashboardPermissionService.ensure_dashboard_authorized(request, dashboard)

        widget = DashboardPermissionService.get_widget_or_raise(
            request, dashboard, widget_name
        )

        filter_defs = DashboardFilterService.resolve_widget_filter_defs(dashboard, widget)
        filters = DashboardFilterService.validate_and_parse(filter_defs, request)

        provider_cls = resolve_provider(widget["provider"])
        provider = provider_cls(
            request=request, dashboard=dashboard, widget=widget, filters=filters
        )

        data = provider.resolve()

        return Response(DashboardResponseService.widget_response(widget["type"], data))


class DashboardWidgetFilterOptionsAPIView(_DashboardEngineAPIView):
    """GET .../widget/<widget_name>/filters/<filter_name>/options/

    Opções de um filtro `select`/`multi_select`/`autocomplete`: ou
    estáticas (`filter_def["options"]`, já declaradas em dashboard.py)
    ou dinâmicas via `filter_def["options_provider"]` (mesmo
    DashboardProviderRegistry dos widgets - reaproveitado, não um
    segundo registry)."""

    def get(self, request, app_name, widget_name, filter_name, *args, **kwargs):
        dashboard = self._get_dashboard_or_404(app_name)

        DashboardPermissionService.ensure_dashboard_authorized(request, dashboard)

        widget = DashboardPermissionService.get_widget_or_raise(
            request, dashboard, widget_name
        )

        filter_defs = DashboardFilterService.resolve_widget_filter_defs(dashboard, widget)
        filter_def = filter_defs.get(filter_name)

        if filter_def is None:
            raise DashboardNotFoundError(f"Filter '{filter_name}' not found.")

        if filter_def.get("options_provider"):
            provider_cls = resolve_provider(filter_def["options_provider"])
            provider = provider_cls(
                request=request, dashboard=dashboard, widget=widget, filters={}
            )
            options = provider.resolve_options()
        else:
            options = filter_def.get("options") or []

        return Response({"options": options})
