"""tooltip + actions (primary_action/actions/row_actions/item_action)
no motor de dashboards - saas/core/dashboards/validator.py +
permissions.py.
"""
import pytest

from django_resaas.saas.core.dashboards.exceptions import DashboardConfigError
from django_resaas.saas.core.dashboards.permissions import DashboardPermissionService
from django_resaas.saas.core.dashboards.validator import DashboardValidator

pytestmark = pytest.mark.django_db


def _base(**overrides):
    config = {
        "schema_version": "1.0",
        "name": "x",
        "label": "X",
        "widgets": [],
        "filters": [],
    }
    config.update(overrides)
    return config


class TestTooltipValidation:

    def test_dashboard_tooltip_must_be_a_string(self):
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(_base(tooltip=123), app_label="x")

    def test_widget_tooltip_must_be_a_string(self):
        config = _base(widgets=[{"name": "w", "type": "stat", "provider": "p", "tooltip": 123}])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_filter_tooltip_must_be_a_string(self):
        config = _base(filters=[{"name": "period", "type": "date_range", "tooltip": 123}])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_valid_tooltips_pass(self):
        config = _base(
            tooltip="Dashboard overview",
            filters=[{"name": "period", "type": "date_range", "tooltip": "Filter by date"}],
            widgets=[{
                "name": "w", "type": "stat", "provider": "p",
                "tooltip": "Widget tooltip",
            }],
        )
        DashboardValidator.validate(config, app_label="x")  # não deve levantar


class TestActionValidation:

    def test_action_missing_type_raises(self):
        config = _base(widgets=[{
            "name": "w", "type": "stat", "provider": "p",
            "actions": [{"name": "view"}],
        }])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_unsupported_action_type_raises(self):
        config = _base(widgets=[{
            "name": "w", "type": "stat", "provider": "p",
            "actions": [{"name": "view", "type": "teleport"}],
        }])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_route_action_without_route_dict_raises(self):
        config = _base(widgets=[{
            "name": "w", "type": "stat", "provider": "p",
            "actions": [{"name": "view", "type": "route"}],
        }])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_duplicate_action_name_raises(self):
        config = _base(widgets=[{
            "name": "w", "type": "stat", "provider": "p",
            "actions": [
                {"name": "view", "type": "refresh"},
                {"name": "view", "type": "fullscreen"},
            ],
        }])
        with pytest.raises(DashboardConfigError, match="duplicad"):
            DashboardValidator.validate(config, app_label="x")

    def test_row_actions_and_primary_action_and_item_action_all_validated(self):
        config = _base(widgets=[{
            "name": "w", "type": "table", "provider": "p",
            "primary_action": {"name": "open", "type": "route", "route": {"name": "list_x"}},
            "row_actions": [{"name": "view", "type": "route", "route": {"name": "view_x"}}],
            "item_action": {"name": "open_item", "type": "route", "route": {"name": "view_x"}},
        }])
        DashboardValidator.validate(config, app_label="x")  # não deve levantar

    def test_invalid_permission_mode_on_action_raises(self):
        config = _base(widgets=[{
            "name": "w", "type": "stat", "provider": "p",
            "actions": [{"name": "view", "type": "refresh", "permission_mode": "whatever"}],
        }])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")

    def test_all_four_supported_action_types_are_valid(self):
        config = _base(widgets=[{
            "name": "w", "type": "stat", "provider": "p",
            "actions": [
                {"name": "a1", "type": "route", "route": {"name": "x"}},
                {"name": "a2", "type": "refresh"},
                {"name": "a3", "type": "fullscreen"},
                {"name": "a4", "type": "dialog"},
            ],
        }])
        DashboardValidator.validate(config, app_label="x")  # não deve levantar


class TestActionPermissionFiltering:

    def _request(self, granted_codenames):
        class FakeRequest:
            pass

        request = FakeRequest()
        request._granted = set(granted_codenames)
        return request

    def _isPermited_stub(self, monkeypatch, request):
        import django_resaas.saas.core.dashboards.permissions as perms_module

        monkeypatch.setattr(
            perms_module, "isPermited",
            lambda request=None, role=None: role in request._granted,
        )

    def test_action_without_permissions_is_always_authorized(self, monkeypatch):
        request = self._request([])
        self._isPermited_stub(monkeypatch, request)

        action = {"name": "refresh", "type": "refresh"}
        assert DashboardPermissionService.can_view_action(request, action) is True

    def test_action_with_permission_user_lacks_is_rejected(self, monkeypatch):
        request = self._request([])
        self._isPermited_stub(monkeypatch, request)

        action = {"name": "create", "type": "route", "permissions": ["add_paciente"]}
        assert DashboardPermissionService.can_view_action(request, action) is False

    def test_widget_visible_but_create_action_hidden_without_add_permission(self, monkeypatch):
        """Cenário exacto do pedido: utilizador vê o widget (tem
        view_paciente) mas não vê a action 'create_patient' (não tem
        add_paciente)."""
        request = self._request(["view_paciente"])
        self._isPermited_stub(monkeypatch, request)

        dashboard_config = {
            "widgets": [{
                "name": "patients", "type": "stat", "provider": "p",
                "permissions": ["view_paciente"],
                "actions": [
                    {"name": "view_patients", "type": "route", "permissions": ["view_paciente"]},
                    {"name": "create_patient", "type": "route", "permissions": ["add_paciente"]},
                ],
            }],
        }

        widgets = DashboardPermissionService.filter_authorized_widgets(request, dashboard_config)

        assert len(widgets) == 1
        action_names = {a["name"] for a in widgets[0]["actions"]}
        assert action_names == {"view_patients"}

    def test_primary_action_and_row_actions_are_filtered_too(self, monkeypatch):
        request = self._request(["view_paciente"])
        self._isPermited_stub(monkeypatch, request)

        dashboard_config = {
            "widgets": [{
                "name": "patients", "type": "table", "provider": "p",
                "primary_action": {"name": "open", "type": "route", "permissions": ["add_paciente"]},
                "row_actions": [
                    {"name": "view", "type": "route", "permissions": ["view_paciente"]},
                    {"name": "delete", "type": "route", "permissions": ["delete_paciente"]},
                ],
            }],
        }

        widgets = DashboardPermissionService.filter_authorized_widgets(request, dashboard_config)

        assert widgets[0]["primary_action"] is None
        assert {a["name"] for a in widgets[0]["row_actions"]} == {"view"}
