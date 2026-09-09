"""Providers de dados dos widgets.

Um widget declara apenas `"provider": "saude.total_pacientes"` em
dashboard.py (string, identificador estável). A resolução para a
classe real acontece EXCLUSIVAMENTE através deste registry - nunca
`import_string(widget["provider"])` sobre um valor não controlado
(o texto do prompt é explícito sobre isto).

Uso:

    from django_resaas.engine.core.dashboards.providers import register_provider, BaseDashboardProvider

    @register_provider("saude.total_pacientes")
    class TotalPacientesProvider(BaseDashboardProvider):
        def resolve(self):
            qs = self.scoped_queryset(Paciente.objects.filter(state="Active"))
            return {"value": qs.count(), "formatted_value": str(qs.count())}
"""

from django_resaas.engine.core.base.dashboard import apply_tenant_scope
from django_resaas.engine.core.dashboards.exceptions import DashboardConfigError

_PROVIDERS = {}


def register_provider(key):
    def decorator(cls):
        if key in _PROVIDERS:
            raise DashboardConfigError(
                f"Provider duplicado: '{key}' já está registado por "
                f"'{_PROVIDERS[key].__module__}.{_PROVIDERS[key].__name__}'.",
                code="duplicate_provider",
            )
        _PROVIDERS[key] = cls
        return cls
    return decorator


def resolve_provider(key):
    provider_cls = _PROVIDERS.get(key)

    if provider_cls is None:
        raise DashboardConfigError(
            f"Provider desconhecido: '{key}'. Nenhum provider foi "
            "registado com este identificador via @register_provider.",
            code="unknown_provider",
        )

    return provider_cls


def clear_providers():
    """Só para testes."""
    _PROVIDERS.clear()


class BaseDashboardProvider:
    """Base para providers de dados de widgets e de opções de filtro.

    `request`/`dashboard`/`widget`/`filters` são sempre passados pelo
    endpoint (views.py) depois de autorização e validação de filtros
    já terem passado - o provider nunca decide segurança, só formata
    dados de um queryset já tenant-scoped.
    """

    def __init__(self, *, request, dashboard, widget, filters):
        self.request = request
        self.dashboard = dashboard
        self.widget = widget
        self.filters = filters or {}

    def scoped_queryset(self, qs):
        """Aplica o mesmo scope branch/entity que TenantDashboardAPIView -
        nunca confiar em entity/branch vindos do frontend."""

        return apply_tenant_scope(
            self.request, qs, module_name=self.dashboard["name"]
        )

    def resolve(self):
        """Deve devolver o payload 'data' do contrato de resposta do
        tipo de widget (ver response.py) - sem a chave 'type', que é
        acrescentada pelo endpoint."""

        raise NotImplementedError

    def resolve_options(self):
        """Usado apenas quando este provider serve como
        'options_provider' de um filtro (ver filters.py). Deve devolver
        uma lista de {'value':..., 'label':...}."""

        raise NotImplementedError
