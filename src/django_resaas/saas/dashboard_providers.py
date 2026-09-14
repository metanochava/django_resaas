"""Providers do dashboard 'django_resaas' (visão de tenancy/plataforma
- ver pages/django_resaas/DashBoard.vue em quasar_resaas, cujos
mesmos 5 KPIs estes widgets replicam). Deliberadamente NÃO usa
scoped_queryset()/apply_tenant_scope(): Entity/EntityType/Branch/User/
App não são dados pertencentes a UM tenant (são os próprios modelos
que DEFINEM os tenants) - contar "quantas Entities existem" já é, por
natureza, uma vista cross-tenant, coerente com a permissão
'view_django_resaas_dashboard' que já protege esta página no
mecanismo antigo (privilégio explícito, nunca implícito - ver
CLAUDE.md secção 6/10)."""

from django_resaas.saas.core.dashboards.providers import (
    BaseDashboardProvider,
    register_provider,
)

from django_resaas.saas.models.app import App
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.user import User


def _stat(value):
    return {"value": value, "formatted_value": str(value)}


@register_provider("django_resaas.total_entities")
class TotalEntitiesProvider(BaseDashboardProvider):

    def resolve(self):
        return _stat(Entity.objects.count())


@register_provider("django_resaas.total_entity_types")
class TotalEntityTypesProvider(BaseDashboardProvider):

    def resolve(self):
        return _stat(EntityType.objects.count())


@register_provider("django_resaas.total_branches")
class TotalBranchesProvider(BaseDashboardProvider):

    def resolve(self):
        return _stat(Branch.objects.count())


@register_provider("django_resaas.total_users")
class TotalUsersProvider(BaseDashboardProvider):

    def resolve(self):
        return _stat(User.objects.count())


@register_provider("django_resaas.total_apps")
class TotalAppsProvider(BaseDashboardProvider):

    def resolve(self):
        return _stat(App.objects.count())
