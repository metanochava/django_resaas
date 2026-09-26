"""The RESAAS error / alert contract (see CLAUDE.md, "ERRORS AND ALERTS").

    error   the failure of the request:  {"error": {"code"?, "message", "details"}}
    alerts  extra messages next to the normal result:  [{"level", "message", "code"?, "details"}]

The HTTP status stays the authority (never repeated in the body), `code` is stable
and never translated, `message` is translated, validation `details` keep the field map.
"""
import pytest
from django.test import override_settings
from rest_framework import serializers
from rest_framework.exceptions import (
    AuthenticationFailed, NotFound, PermissionDenied, Throttled, ValidationError,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView

from django_resaas.saas.core.alerts import LEVELS, add_alert, build_alert, merge_alerts, pending_alerts
from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin
from django_resaas.saas.core.exceptions import ConflictError, ResaasAPIException, error_body, resaas_exception_handler

pytestmark = pytest.mark.django_db

factory = APIRequestFactory()


def _handle(exc, lang=None):
    extra = {"HTTP_L": lang} if lang else {}
    request = factory.get("/", **extra)
    return resaas_exception_handler(exc, {"request": request, "view": object()})


# ------------------------------------------------------------------ the error contract

class TestErrorContract:

    def test_permission_denied_is_403_with_a_code_and_a_message(self):
        response = _handle(PermissionDenied())

        assert response.status_code == 403
        assert response.data["error"] == {
            "code": "permission_denied",
            "message": "You do not have permission to perform this action.",
            "details": None,
        }

    def test_not_found_and_authentication_failed_keep_their_status(self):
        assert _handle(NotFound()).status_code == 404
        assert _handle(NotFound()).data["error"]["code"] == "not_found"

        failed = _handle(AuthenticationFailed("Invalid credentials"))
        assert failed.status_code == 401
        assert failed.data["error"]["message"] == "Invalid credentials"
        assert failed.data["error"]["code"] == "authentication_failed"

    def test_throttled_keeps_status_and_retry_after(self):
        response = _handle(Throttled(wait=12))

        assert response.status_code == 429
        assert response["Retry-After"] == "12"
        assert response.data["error"]["code"] == "throttled"

    def test_a_conflict_carries_its_own_code_and_409(self):
        response = _handle(ConflictError("This profile is already assigned.", code="group_already_assigned"))

        assert response.status_code == 409
        assert response.data["error"] == {
            "code": "group_already_assigned",
            "message": "This profile is already assigned.",
            "details": None,
        }

    def test_an_exception_without_a_code_publishes_none_not_drf_generic_one(self):
        response = _handle(ResaasAPIException("Something is wrong."))

        assert "code" not in response.data["error"]
        assert response.data["error"]["message"] == "Something is wrong."
        assert response.data["error"]["details"] is None

    def test_structured_details_are_kept(self):
        response = _handle(ResaasAPIException("Partly done.", code="partial", details={"failed": ["a", "b"]}))

        assert response.data["error"]["details"] == {"failed": ["a", "b"]}

    def test_the_status_is_not_repeated_in_the_body_and_there_is_no_success_flag(self):
        body = _handle(ConflictError("x", code="c")).data

        assert "status" not in body and "success" not in body
        assert "status" not in body["error"]

    def test_validation_errors_keep_the_field_map_in_details(self):
        response = _handle(ValidationError({"email": ["This email is already in use."], "mobile": ["Invalid number."]}))

        assert response.status_code == 400
        assert response.data["error"]["message"] == "Please correct the highlighted fields."
        assert response.data["error"]["details"] == {
            "email": ["This email is already in use."],
            "mobile": ["Invalid number."],
        }
        assert "code" not in response.data["error"]

    def test_nested_and_non_field_validation_errors_keep_their_shape(self):
        nested = _handle(ValidationError({"address": {"country_code": ["Invalid."]}}))
        assert nested.data["error"]["details"] == {"address": {"country_code": ["Invalid."]}}

        plain = _handle(ValidationError(["Only one of these may be set."]))
        assert plain.data["error"]["details"] == ["Only one of these may be set."]


class TestDictDetailWithCode:

    def test_an_exception_raised_with_code_and_detail_is_one_error_with_that_code(self):
        response = _handle(AuthenticationFailed({"code": "temporary_password_expired", "detail": "The temporary password has expired."}))

        assert response.status_code == 401
        assert response.data["error"] == {
            "code": "temporary_password_expired",
            "message": "The temporary password has expired.",
            "details": None,
        }


class TestNoLegacyAliases:
    """The old {"detail": ..., "code": ...} + bare field map aliases were removed
    once every consumer (django_resaas, quasar_resaas, dev/front, pro/front) was
    migrated onto `error`/`errorMessage()`/`errorCode()`. `error` is now the only
    top-level key a failed request answers with - this is a regression guard."""

    def test_no_top_level_detail_or_code_next_to_error(self):
        body = _handle(ConflictError("Already assigned.", code="group_already_assigned")).data

        assert body == {"error": {"code": "group_already_assigned", "message": "Already assigned.", "details": None}}

    def test_validation_does_not_keep_the_bare_field_map(self):
        body = _handle(ValidationError({"email": ["Taken."]})).data

        assert "email" not in body
        assert body["error"]["details"]["email"] == ["Taken."]

    def test_a_field_literally_named_error_does_not_leak_into_the_top_level(self):
        body = _handle(ValidationError({"error": ["a field literally named error"]})).data

        assert body["error"]["message"] == "Please correct the highlighted fields."
        assert body["error"]["details"] == {"error": ["a field literally named error"]}


class TestTranslation:

    def test_the_message_is_translated_with_the_request_language(self):
        assert _handle(ValidationError({"a": ["x"]}), lang="pt-pt").data["error"]["message"] == "Corrija os campos assinalados."
        assert _handle(ValidationError({"a": ["x"]}), lang="fr-fr").data["error"]["message"] == "Veuillez corriger les champs signalés."

    def test_the_code_is_never_translated(self):
        english = _handle(PermissionDenied(), lang="en-us").data["error"]["code"]
        portuguese = _handle(PermissionDenied(), lang="pt-pt").data["error"]["code"]
        spanish = _handle(PermissionDenied(), lang="es-es").data["error"]["code"]

        assert english == portuguese == spanish == "permission_denied"

    def test_a_drf_default_message_is_translated(self):
        assert _handle(PermissionDenied(), lang="pt-pt").data["error"]["message"] == "Não tem permissão para realizar esta operação."

    def test_validation_messages_inside_details_go_through_the_translator(self):
        response = _handle(ValidationError({"a": ["Not found."]}), lang="pt-pt")

        assert response.data["error"]["details"]["a"] == ["Não encontrado."]


class TestUnexpectedErrors:

    def _boom(self):
        return _handle(RuntimeError("SELECT * FROM users WHERE token='secret-123' at /var/www/dev/back/x.py"))

    @override_settings(DEBUG=False)
    def test_a_500_is_generic_and_leaks_nothing(self):
        response = self._boom()

        assert response.status_code == 500
        text = str(response.data)
        assert "SELECT" not in text and "secret-123" not in text and "/var/www" not in text and "RuntimeError" not in text
        assert response.data["error"]["message"] == "An unexpected error occurred. Please try again later."

    @override_settings(DEBUG=False)
    def test_the_full_error_is_logged_on_the_server(self, caplog):
        with caplog.at_level("ERROR"):
            self._boom()

        assert "Unhandled exception" in caplog.text

    @override_settings(DEBUG=True)
    def test_with_debug_on_django_keeps_its_own_debug_page(self):
        assert self._boom() is None


# ------------------------------------------------------------------ alerts

class TestAlertBuilding:

    def test_a_valid_alert_has_level_message_and_optional_code(self):
        request = factory.get("/")

        assert build_alert(request, "Saved.", level="success") == {"level": "success", "message": "Saved.", "details": None}
        assert build_alert(request, "No profile.", level="warning", code="employee_without_profile")["code"] == "employee_without_profile"

    def test_only_the_backend_levels_are_accepted(self):
        request = factory.get("/")

        assert LEVELS == ("success", "info", "warning", "error")
        for wrong in ("negative", "positive", "danger", ""):
            with pytest.raises(ValueError):
                build_alert(request, "x", level=wrong)

    def test_a_message_is_required(self):
        with pytest.raises(ValueError):
            build_alert(factory.get("/"), "", level="info")

    def test_the_message_is_translated_and_the_code_is_not(self):
        alert = build_alert(factory.get("/", HTTP_L="pt-pt"), "Not found.", level="info", code="not_found")

        assert alert["message"] == "Não encontrado."
        assert alert["code"] == "not_found"

    def test_alerts_belong_to_their_own_request(self):
        first, second = factory.get("/"), factory.get("/")

        # messages that are no translation key (tdc matches keys regardless of case)
        add_alert(first, "first alert x1")
        add_alert(first, "first alert x2", level="warning")
        add_alert(second, "second alert x3")

        assert [a["message"] for a in pending_alerts(first)] == ["first alert x1", "first alert x2"]
        assert [a["message"] for a in pending_alerts(second)] == ["second alert x3"]

    def test_merge_adds_to_a_dict_only(self):
        request = factory.get("/")
        add_alert(request, "hello")

        assert merge_alerts(request, {"id": 1})["alerts"][0]["message"] == "hello"
        assert merge_alerts(request, [1, 2]) == [1, 2]
        assert merge_alerts(factory.get("/"), {"id": 1}) == {"id": 1}

    def test_merge_keeps_alerts_the_view_already_put_in_the_body(self):
        request = factory.get("/")
        add_alert(request, "queued")

        merged = merge_alerts(request, {"alerts": [{"level": "info", "message": "inline"}]})

        assert [a["message"] for a in merged["alerts"]] == ["inline", "queued"]


class _Demo(ResaasResponseMixin, APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request):
        kind = request.query_params.get("kind")

        if kind == "plain":
            return Response({"id": 1})
        if kind == "one":
            add_alert(request, "Employee created.", level="success")
            return Response({"id": 1})
        if kind == "many":
            add_alert(request, "Employee created.", level="success")
            add_alert(request, "No profile yet.", level="warning", code="employee_without_profile")
            return Response({"id": 1})
        if kind == "list":
            add_alert(request, "ignored: a bare list cannot carry it")
            return Response([1, 2])
        if kind == "error_and_alerts":
            add_alert(request, "Nothing was saved.", level="info")
            raise ConflictError("Already assigned.", code="group_already_assigned")
        if kind == "boom":
            raise RuntimeError("SELECT secret")
        return Response({})


def _call(kind, **extra):
    view = _Demo.as_view()
    return view(factory.get("/", {"kind": kind}, **extra))


class TestAlertsOnResponses:

    def test_a_normal_response_without_alerts_is_untouched(self):
        assert _call("plain").data == {"id": 1}

    def test_one_alert_keeps_the_normal_payload(self):
        data = _call("one").data

        assert data["id"] == 1
        assert data["alerts"] == [{"level": "success", "message": "Employee created.", "details": None}]

    def test_several_alerts_are_all_delivered_in_order(self):
        alerts = _call("many").data["alerts"]

        assert [a["level"] for a in alerts] == ["success", "warning"]
        assert alerts[1]["code"] == "employee_without_profile"

    def test_a_bare_list_payload_is_left_alone(self):
        assert _call("list").data == [1, 2]

    def test_an_error_response_can_carry_extra_alerts_but_not_repeat_its_own_error(self):
        response = _call("error_and_alerts")

        assert response.status_code == 409
        assert response.data["error"]["code"] == "group_already_assigned"
        assert [a["message"] for a in response.data["alerts"]] == ["Nothing was saved."]
        assert "Already assigned." not in [a["message"] for a in response.data["alerts"]]

    @override_settings(DEBUG=False)
    def test_an_unexpected_error_through_a_view_is_a_generic_500(self):
        response = _call("boom")

        assert response.status_code == 500
        assert "SELECT" not in str(response.data)


# ------------------------------------------------------------------ the real endpoints

class TestRealEndpoints:

    def test_an_anonymous_call_to_a_protected_endpoint_answers_401_with_the_contract(self):
        response = APIClient().get("/api/two_factor/")

        assert response.status_code == 401
        assert response.data["error"]["code"] == "not_authenticated"
        assert response.data["error"]["message"]

    def test_wrong_credentials_answer_401_with_the_contract(self):
        response = APIClient().post("/api/login/", {"identifier": "nobody", "password": "nope"}, format="json")

        assert response.status_code == 401
        assert response.data["error"]["message"] == "Invalid credentials"
        assert "detail" not in response.data

    def test_a_missing_permission_on_a_base_view_is_403_with_a_code(self, bootstrap_tenant):
        from django_resaas.saas.models.group import Group
        from django_resaas.saas.core.tenant.context import ResaasContextService

        tenant = bootstrap_tenant("contract-403")
        guest = Group.objects.get(name="Guest")
        context = ResaasContextService.issue(
            user=tenant["user"], entity_id=tenant["entity"].id, branch_id=tenant["branch"].id, group_id=guest.id,
        )
        tenant["client"].credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")

        response = tenant["client"].get("/api/hr/departments/")

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"
        assert "detail" not in response.data

    def test_a_validation_error_on_a_base_view_keeps_the_field_map(self, bootstrap_tenant):
        tenant = bootstrap_tenant("contract-validation")

        response = tenant["client"].post("/api/hr/departments/", {"name": ""}, format="json")

        assert response.status_code == 400
        assert "name" in response.data["error"]["details"]
        assert "name" not in response.data

    def test_another_tenants_object_is_a_plain_404_that_leaks_nothing(self, bootstrap_tenant):
        from django_resaas.hr.models.department import Department

        mine = bootstrap_tenant("contract-mine")
        other = bootstrap_tenant("contract-other")
        secret = Department.objects.create(entity=other["entity"], branch=other["branch"], name="Secret Oncology Unit")

        response = mine["client"].get(f"/api/hr/departments/{secret.id}/")

        assert response.status_code == 404
        text = str(response.data)
        assert "Secret Oncology Unit" not in text and str(secret.id) not in text
        assert response.data["error"]["code"] == "not_found"

    def test_two_factor_errors_carry_a_stable_code_and_the_contract(self):
        from django_resaas.saas.models.user import User

        user = User.objects.create_user(username="tf-contract", email="tf@contract.test", password="Own-Password-1")
        client = APIClient(raise_request_exception=False)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {user.tokens()['access']}")

        response = client.post("/api/two_factor/disable/", {"code": "123456"}, format="json")

        assert response.status_code == 409
        assert response.data["error"]["code"] == "two_factor_not_active"
        assert "code" not in response.data

    def test_a_resaas_action_denial_uses_the_same_contract(self, bootstrap_tenant):
        tenant = bootstrap_tenant("contract-action")
        stranger = tenant["client"].get("/api/django_resaas/users/00000000-0000-0000-0000-000000000000/passwordSecurity/")

        assert stranger.status_code in (403, 404)
        assert "error" in stranger.data


class TestSetupIsNotBroken:

    def test_importing_the_error_layer_does_not_freeze_drf_defaults(self):
        """settings.py imports django_resaas.saas.core.utils while REST_FRAMEWORK is not
        defined yet. If that import chain reached rest_framework.views, DRF would cache
        its DEFAULTS (Session/Basic auth, no RESAAS handler, ...) for the whole process."""
        from rest_framework.settings import api_settings

        assert api_settings.EXCEPTION_HANDLER is resaas_exception_handler
        assert [c.__name__ for c in api_settings.DEFAULT_AUTHENTICATION_CLASSES][0] == "JWTAuthentication"

    def test_the_handler_module_does_not_import_rest_framework_views_at_import_time(self):
        import inspect
        from django_resaas.saas.core.exceptions import handler

        module_level = inspect.getsource(handler).split("def resaas_exception_handler")[0]

        assert "rest_framework.views" not in module_level
