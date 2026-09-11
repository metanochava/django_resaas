"""Motor de dashboards dinâmicos (saas/core/dashboards/).

Usa `dev.demo` (app real, mínima, já existente para demonstrar o
fluxo completo do framework) + `dev/demo/dashboard.py` (criado para
este motor) como fixture - discovery/permissões/filtros são testados
contra uma app real, não um mock.
"""
from unittest import mock

import pytest
from rest_framework.test import APIClient

from django_resaas.saas.core.dashboards import discovery, providers, registry
from django_resaas.saas.core.dashboards.exceptions import DashboardConfigError
from django_resaas.saas.core.dashboards.filters import DashboardFilterService
from django_resaas.saas.core.dashboards.validator import DashboardValidator
from django_resaas.saas.core.tenant.context import ResaasContextService
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.group import Group

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _reset_discovery():
    """Cada teste começa com uma descoberta limpa - discover() é
    idempotente/cacheado por processo (ver discovery.py), o que
    esconderia efeitos entre testes que mockam import_module."""
    discovery.DashboardDiscoveryService.reset()
    yield
    discovery.DashboardDiscoveryService.reset()
    discovery.DashboardDiscoveryService.discover()


# ============================================================
# DISCOVERY
# ============================================================

class TestDiscovery:

    def test_app_without_dashboard_py_is_ignored(self):
        discovery.DashboardDiscoveryService.discover(force=True)
        # django_resaas.notifications não tem dashboard.py (tem
        # views/dashboard.py, um endpoint TenantDashboardAPIView, não
        # o novo <app>/dashboard.py declarativo) - não deve dar erro
        # nem aparecer no registry deste motor.
        assert registry.DashboardRegistry.get("notifications") is None

    def test_finds_real_demo_dashboard(self):
        discovery.DashboardDiscoveryService.discover(force=True)
        dashboard = registry.DashboardRegistry.get("demo")

        assert dashboard is not None
        assert dashboard["label"] == "Demo"
        widget_names = {w["name"] for w in dashboard["widgets"]}
        assert widget_names == {"total_products", "products_table"}

    def test_broken_internal_import_inside_dashboard_py_is_never_hidden(self):
        real_import = discovery.importlib.import_module

        def fake_import(name, *args, **kwargs):
            if name == "dev.demo.dashboard":
                raise ModuleNotFoundError(
                    "No module named 'dev.demo.a_typo_that_does_not_exist'",
                    name="dev.demo.a_typo_that_does_not_exist",
                )
            return real_import(name, *args, **kwargs)

        with mock.patch.object(discovery.importlib, "import_module", side_effect=fake_import):
            with pytest.raises(ModuleNotFoundError):
                discovery.DashboardDiscoveryService.discover(force=True)

    def test_duplicate_dashboard_name_is_rejected_keeping_the_first(self):
        registry.DashboardRegistry.clear()

        first = {"schema_version": "1.0", "name": "dup", "label": "First", "widgets": []}
        second = {"schema_version": "1.0", "name": "dup", "label": "Second", "widgets": []}

        assert registry.DashboardRegistry.register("dup", first, app_label="a") is True
        assert registry.DashboardRegistry.register("dup", second, app_label="b") is False

        assert registry.DashboardRegistry.get("dup")["label"] == "First"
        assert any("duplicado" in msg for msg in registry.DashboardRegistry.get_errors())


# ============================================================
# IMUTABILIDADE
# ============================================================

class TestRegistryImmutability:

    def test_mutating_a_read_never_affects_the_global_config_or_later_reads(self):
        registry.DashboardRegistry.clear()
        registry.DashboardRegistry.register(
            "immut",
            {"schema_version": "1.0", "name": "immut", "label": "L",
             "widgets": [{"name": "w1", "type": "stat", "provider": "x"}]},
            app_label="immut",
        )

        # Simula o que DashboardDetailAPIView faz para User A: filtra
        # (muta) a config lida.
        user_a_view = registry.DashboardRegistry.get("immut")
        user_a_view["widgets"] = []
        user_a_view["label"] = "Hacked by User A"

        # User B, requisição nova.
        user_b_view = registry.DashboardRegistry.get("immut")

        assert user_b_view["label"] == "L"
        assert len(user_b_view["widgets"]) == 1
        assert user_b_view["widgets"][0]["name"] == "w1"


# ============================================================
# VALIDATOR
# ============================================================

class TestValidator:

    def _base(self, **overrides):
        config = {
            "schema_version": "1.0",
            "name": "x",
            "label": "X",
            "widgets": [],
            "filters": [],
        }
        config.update(overrides)
        return config

    def test_unknown_schema_version_raises(self):
        with pytest.raises(DashboardConfigError, match="schema_version"):
            DashboardValidator.validate(self._base(schema_version="9.9"), app_label="x")

    def test_missing_required_field_raises(self):
        config = self._base()
        del config["label"]
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_duplicate_widget_name_raises(self):
        config = self._base(widgets=[
            {"name": "w", "type": "stat", "provider": "p1"},
            {"name": "w", "type": "stat", "provider": "p2"},
        ])
        with pytest.raises(DashboardConfigError, match="duplicad"):
            DashboardValidator.validate(config, app_label="x")

    def test_widget_missing_provider_raises(self):
        config = self._base(widgets=[{"name": "w", "type": "stat"}])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_duplicate_filter_name_raises(self):
        config = self._base(filters=[
            {"name": "f", "type": "text"},
            {"name": "f", "type": "date"},
        ])
        with pytest.raises(DashboardConfigError, match="duplicad"):
            DashboardValidator.validate(config, app_label="x")

    def test_unknown_filter_type_raises(self):
        config = self._base(filters=[{"name": "f", "type": "heatmap"}])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_invalid_permission_mode_raises(self):
        config = self._base(widgets=[
            {"name": "w", "type": "stat", "provider": "p", "permission_mode": "some"},
        ])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_accepts_filters_referencing_unknown_filter_raises(self):
        config = self._base(widgets=[
            {"name": "w", "type": "stat", "provider": "p", "accepts_filters": ["ghost"]},
        ])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_valid_config_passes(self):
        config = self._base(
            filters=[{"name": "period", "type": "date_range"}],
            widgets=[
                {"name": "w", "type": "stat", "provider": "p", "accepts_filters": ["period"]},
            ],
        )
        DashboardValidator.validate(config, app_label="x")  # não deve levantar


# ============================================================
# PROVIDER REGISTRY
# ============================================================

class TestProviderRegistry:

    def test_unknown_provider_raises_config_error(self):
        with pytest.raises(DashboardConfigError, match="desconhecido"):
            providers.resolve_provider("nao.existe")

    def test_never_resolves_via_import_string_style_path(self):
        # Um provider "malicioso" nunca registado não pode ser
        # resolvido só porque o nome parece um caminho de import
        # válido.
        with pytest.raises(DashboardConfigError):
            providers.resolve_provider("django_resaas.saas.models.user.User")

    def test_register_provider_with_aliases_resolves_both_to_same_class(self):
        # Internacionalização de identificadores (ex.: "saude.
        # total_pacientes" -> "saude.total_patients") sem quebrar
        # nenhum dashboard.py que ainda referencie o nome antigo - ver
        # docs/architecture/dashboards.md.
        try:
            @providers.register_provider("t.new_name", aliases=["t.old_name"])
            class _Provider(providers.BaseDashboardProvider):
                def resolve(self):
                    return {"value": 1}

            assert providers.resolve_provider("t.new_name") is _Provider
            assert providers.resolve_provider("t.old_name") is _Provider
        finally:
            providers._PROVIDERS.pop("t.new_name", None)
            providers._PROVIDERS.pop("t.old_name", None)

    def test_register_provider_alias_collision_raises(self):
        try:
            @providers.register_provider("t.a")
            class _A(providers.BaseDashboardProvider):
                def resolve(self):
                    return {}

            with pytest.raises(DashboardConfigError, match="duplicado"):
                @providers.register_provider("t.b", aliases=["t.a"])
                class _B(providers.BaseDashboardProvider):
                    def resolve(self):
                        return {}

            # A colisão no alias não deve deixar 't.b' registado a meio.
            with pytest.raises(DashboardConfigError):
                providers.resolve_provider("t.b")
        finally:
            providers._PROVIDERS.pop("t.a", None)
            providers._PROVIDERS.pop("t.b", None)


# ============================================================
# FILTER SERVICE
# ============================================================

class TestFilterService:

    def _req(self, params):
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        django_request = factory.get("/", params)
        request = Request(django_request)
        request.entity_id = "11111111-1111-1111-1111-111111111111"
        request.branch_id = "22222222-2222-2222-2222-222222222222"
        return request

    def test_unknown_param_is_rejected(self):
        defs = {"search": {"name": "search", "type": "search"}}
        request = self._req({"search": "x", "bogus": "1"})
        with pytest.raises(Exception) as exc_info:
            DashboardFilterService.validate_and_parse(defs, request)
        assert "bogus" in str(exc_info.value.fields)

    def test_date_range_parses_from_to(self):
        defs = {"period": {"name": "period", "type": "date_range"}}
        request = self._req({"period_from": "2026-01-01", "period_to": "2026-01-31"})
        parsed = DashboardFilterService.validate_and_parse(defs, request)
        assert parsed["period"]["from"].isoformat() == "2026-01-01"
        assert parsed["period"]["to"].isoformat() == "2026-01-31"

    def test_date_range_inverted_is_rejected(self):
        defs = {"period": {"name": "period", "type": "date_range"}}
        request = self._req({"period_from": "2026-02-01", "period_to": "2026-01-01"})
        with pytest.raises(Exception):
            DashboardFilterService.validate_and_parse(defs, request)

    def test_multi_select_uses_repeated_keys(self):
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        django_request = factory.get("/?status=a&status=b")
        request = Request(django_request)
        request.entity_id = "e"
        request.branch_id = "b"

        defs = {"status": {"name": "status", "type": "multi_select"}}
        parsed = DashboardFilterService.validate_and_parse(defs, request)
        assert parsed["status"] == ["a", "b"]

    def test_entity_filter_cannot_cross_tenant(self):
        defs = {"entity": {"name": "entity", "type": "entity"}}
        request = self._req({"entity": "99999999-9999-9999-9999-999999999999"})
        with pytest.raises(Exception):
            DashboardFilterService.validate_and_parse(defs, request)

    def test_entity_filter_defaults_to_request_context(self):
        defs = {"entity": {"name": "entity", "type": "entity"}}
        request = self._req({})
        parsed = DashboardFilterService.validate_and_parse(defs, request)
        assert parsed["entity"] == str(request.entity_id)


# ============================================================
# ENDPOINTS (integração HTTP completa via bootstrap_tenant)
# ============================================================

class TestDashboardEndpoints:

    def _guest_client(self, tenant):
        """Mesmo padrão já usado nesta sessão para testes de 'sem
        permissão' - Group.name é único globalmente, por isso um
        segundo bootstrap_tenant('Root') no mesmo teste 'herdaria'
        permissões já concedidas a Root por outro teste. Um grupo
        Guest fresco + client isolado evita isso."""
        guest_group, _ = Group.objects.get_or_create(name=f"Guest-{tenant['entity'].id}")

        BranchUserGroup.objects.get_or_create(
            user=tenant["user"], branch=tenant["branch"], group=guest_group,
            defaults={"state": 1},
        )

        context = ResaasContextService.issue(
            user=tenant["user"], entity_id=tenant["entity"].id,
            branch_id=tenant["branch"].id, group_id=guest_group.id,
        )

        client = APIClient()
        client.force_authenticate(user=tenant["user"])
        client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")
        return client

    def test_dashboard_list_requires_tenant_context(self):
        client = APIClient()
        response = client.get("/api/django_resaas/dashboards/?format=json")
        assert response.status_code in (401, 403)

    def test_inactive_module_returns_403_on_detail(self, bootstrap_tenant):
        tenant = bootstrap_tenant("dash-inactive")  # 'demo' não activado

        response = tenant["client"].get("/api/django_resaas/dashboard/demo/?format=json")

        assert response.status_code == 403
        assert response.data["error"]["code"] == "module_not_active"

    def test_widget_data_returns_stat_contract(self, bootstrap_tenant):
        from dev.demo.models import Product

        tenant = bootstrap_tenant("dash-stat", modules=("demo",))
        Product.objects.create(
            name="Caneta", sku="P1", price=10,
            entity=tenant["entity"], branch=tenant["branch"],
            created_by=tenant["user"], updated_by=tenant["user"], state="Active",
        )

        response = tenant["client"].get(
            "/api/django_resaas/dashboard/demo/widget/total_products/?format=json"
        )

        assert response.status_code == 200, response.data
        assert response.data["type"] == "stat"
        assert response.data["data"]["value"] == 1

    def test_widget_table_pagination_contract(self, bootstrap_tenant):
        from dev.demo.models import Product

        tenant = bootstrap_tenant("dash-table", modules=("demo",))
        for i in range(3):
            Product.objects.create(
                name=f"Item {i}", sku=f"P{i}", price=10,
                entity=tenant["entity"], branch=tenant["branch"],
                created_by=tenant["user"], updated_by=tenant["user"], state="Active",
            )

        response = tenant["client"].get(
            "/api/django_resaas/dashboard/demo/widget/products_table/"
            "?format=json&page=1&page_size=2"
        )

        assert response.status_code == 200, response.data
        assert response.data["type"] == "table"
        assert len(response.data["data"]["rows"]) == 2
        assert response.data["data"]["pagination"]["count"] == 3

    def test_widget_without_permission_returns_403_not_empty_data(self, bootstrap_tenant):
        tenant = bootstrap_tenant("dash-noperm", modules=("demo",))
        client = self._guest_client(tenant)

        response = client.get(
            "/api/django_resaas/dashboard/demo/widget/total_products/?format=json"
        )

        assert response.status_code == 403
        assert "data" not in response.data

    def test_direct_widget_endpoint_is_protected_independently_of_detail(self, bootstrap_tenant):
        """Um pedido directo ao endpoint do widget, sem nunca ter
        pedido /dashboard/demo/ primeiro, continua protegido."""
        tenant = bootstrap_tenant("dash-direct", modules=("demo",))
        client = self._guest_client(tenant)

        response = client.get(
            "/api/django_resaas/dashboard/demo/widget/products_table/?format=json"
        )

        assert response.status_code == 403

    def test_detail_never_returns_unauthorized_widgets(self, bootstrap_tenant):
        tenant = bootstrap_tenant("dash-detail-noperm", modules=("demo",))
        client = self._guest_client(tenant)

        response = client.get("/api/django_resaas/dashboard/demo/?format=json")

        assert response.status_code == 200, response.data
        assert response.data["dashboard"]["widgets"] == []

    def test_unknown_filter_param_returns_400(self, bootstrap_tenant):
        tenant = bootstrap_tenant("dash-badfilter", modules=("demo",))

        response = tenant["client"].get(
            "/api/django_resaas/dashboard/demo/widget/total_products/"
            "?format=json&not_a_real_filter=1"
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "invalid_filter"

    def test_unknown_dashboard_returns_404(self, bootstrap_tenant):
        tenant = bootstrap_tenant("dash-404", modules=("demo",))

        response = tenant["client"].get(
            "/api/django_resaas/dashboard/does_not_exist/?format=json"
        )

        assert response.status_code == 404

    def test_dashboard_list_only_includes_authorized_and_active(self, bootstrap_tenant):
        tenant = bootstrap_tenant("dash-list")  # 'demo' não activado

        response = tenant["client"].get("/api/django_resaas/dashboards/?format=json")

        assert response.status_code == 200
        names = {d["name"] for d in response.data}
        assert "demo" not in names
