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
                "name": "w", "type": "stat", "provider": "p", "cols": {"xs": 12},
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
            "name": "w", "type": "table", "provider": "p", "cols": {"xs": 12},
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
            "name": "w", "type": "stat", "provider": "p", "cols": {"xs": 12},
            "actions": [
                {"name": "a1", "type": "route", "route": {"name": "x"}},
                {"name": "a2", "type": "refresh"},
                {"name": "a3", "type": "fullscreen"},
                {"name": "a4", "type": "dialog", "dialog": "demo.form"},
            ],
        }])
        DashboardValidator.validate(config, app_label="x")  # não deve levantar

    def test_request_action_needs_a_write_method_and_an_endpoint(self):
        def config(action):
            return _base(widgets=[{"name": "w", "type": "stat", "provider": "p", "cols": {"xs": 12},
                                   "actions": [action]}])

        DashboardValidator.validate(config({
            "name": "ok", "type": "request", "request": {"method": "post", "endpoint": "x/{id}/do/"},
            "when": {"field": "estado", "in": ["a"]},
        }), app_label="x")

        for bad in (
            {"name": "r", "type": "request"},
            {"name": "r", "type": "request", "request": {"method": "GET", "endpoint": "x/"}},
            {"name": "r", "type": "request", "request": {"method": "POST"}},
            {"name": "r", "type": "refresh", "when": "estado=a"},
        ):
            with pytest.raises(DashboardConfigError):
                DashboardValidator.validate(config(bad), app_label="x")

    def test_dialog_action_needs_the_dialog_name(self):
        # the frontend opens the dialog registered under that name
        config = _base(widgets=[{
            "name": "w", "type": "stat", "provider": "p", "cols": {"xs": 12},
            "actions": [{"name": "a4", "type": "dialog"}],
        }])
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(config, app_label="x")


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


class TestDblclickAction:
    """dblclick_action: a second action on the same button (double click),
    validated like any action and filtered on its own permissions."""

    LIST = {"name": "patients", "type": "route", "route": {"name": "list_paciente"},
            "permissions": ["list_paciente"],
            "dblclick_action": {"name": "patients_dialog", "type": "dialog", "dialog": "saude.patient_list",
                                "permissions": ["list_paciente", "view_paciente"], "permission_mode": "all"}}

    def _widget(self, action):
        return _base(widgets=[{"name": "w", "type": "stat", "provider": "p", "actions": [action],
                               "cols": {"xs": 12, "sm": 12, "md": 12, "lg": 12, "xl": 12}}])

    def test_a_valid_dblclick_action_passes(self):
        DashboardValidator.validate(self._widget(self.LIST), app_label="x")

    def test_the_dblclick_action_is_validated_like_any_action(self):
        broken = {**self.LIST, "dblclick_action": {"name": "d", "type": "dialog"}}   # no "dialog"
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(self._widget(broken), app_label="x")

    def test_it_cannot_nest_another_dblclick_action(self):
        nested = {**self.LIST, "dblclick_action": {**self.LIST["dblclick_action"], "dblclick_action": {}}}
        with pytest.raises(DashboardConfigError):
            DashboardValidator.validate(self._widget(nested), app_label="x")

    def _filter(self, monkeypatch, granted):
        request = TestActionPermissionFiltering()._request(granted)
        TestActionPermissionFiltering()._isPermited_stub(monkeypatch, request)
        return DashboardPermissionService.filter_authorized_actions(request, [self.LIST])

    def test_with_both_permissions_the_double_click_stays(self, monkeypatch):
        actions = self._filter(monkeypatch, ["list_paciente", "view_paciente"])

        assert actions[0]["dblclick_action"]["dialog"] == "saude.patient_list"

    def test_without_its_permissions_only_the_double_click_is_dropped(self, monkeypatch):
        actions = self._filter(monkeypatch, ["list_paciente"])

        assert actions[0]["name"] == "patients"
        assert "dblclick_action" not in actions[0]
        assert "dblclick_action" in self.LIST          # the registered config is not changed

    def test_without_the_main_permission_nothing_is_returned(self, monkeypatch):
        assert self._filter(monkeypatch, ["view_paciente"]) == []
