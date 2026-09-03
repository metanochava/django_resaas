"""
FASE 2 - P1.1: freezes the real, over-the-wire Schema 1.0 contract served
by `GET .../resaasapps/{app}/{model}/schema/` (AppSchemaAPIView.model_schema
in management/apicommands/view/app_schema.py).

`core/schema/tests/test_builder.py` already covers `ResaasSchemaBuilder`
as a unit (given a `fields=` list) exhaustively - routes/ui/filters/
pagination/pdf merge behavior, actions ordering, etc. This file instead
exercises the piece that ISN'T covered there: `_schema_fields()`, the
Django-field-introspection logic in app_schema.py that actually builds
that `fields=` list from a real model, and the full JSON response as it
comes back over HTTP (through DRF's Response/JSON layer, not just the
Python dict `.build()` returns).

Two real, already-migrated models are used - no new migrations:
- hr.SalaryComponent: CharField, ChoiceField (via choices=), DecimalField,
  BooleanField
- hr.Attendance: ForeignKey, DateField, DateTimeField, IntegerField
"""
import pytest
from rest_framework.viewsets import ModelViewSet

from django_resaas.engine.core.decorators.action import resaas_action
from django_resaas.engine.core.services.action_sync_service import ActionSyncService

pytestmark = pytest.mark.django_db


def _schema(client, app, model):
    response = client.get(f"/api/django_resaas/resaasapps/{app}/{model}/schema/")
    assert response.status_code == 200, response.data
    return response.data


def _field(schema, name):
    return next(f for f in schema["fields"] if f["name"] == name)


# =========================================================
# ENVELOPE / TOP-LEVEL CONTRACT
# =========================================================

def test_schema_has_every_documented_top_level_key(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-envelope-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    for key in (
        "schema_version", "model", "fields", "actions", "permissions",
        "routes", "ui", "filters", "pagination", "pdf",
    ):
        assert key in schema, f"missing top-level key: {key}"


def test_schema_version_is_1_0(bootstrap_tenant):
    """The version must never change silently - a future incompatible
    change to this contract has to bump SCHEMA_VERSION explicitly."""
    tenant = bootstrap_tenant("schema-version-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    assert schema["schema_version"] == "1.0"


def test_model_metadata_is_exposed(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-model-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    assert schema["model"]["app"] == "hr"
    assert schema["model"]["name"] == "salarycomponent"
    assert schema["model"]["class_name"] == "SalaryComponent"
    assert schema["model"]["pk"] == "id"
    # backend endpoint must prevail - frontend never re-derives this
    assert schema["model"]["endpoint"] == "hr/salarycomponents/"


def test_permissions_are_backend_computed(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-permissions-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    assert schema["permissions"]["list"] == "list_salarycomponent"
    assert schema["permissions"]["add"] == "add_salarycomponent"
    assert schema["permissions"]["delete"] == "delete_salarycomponent"
    assert "custom" in schema["permissions"]


def test_routes_default_convention(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-routes-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    assert schema["routes"]["list"] == "list_salarycomponent"
    assert schema["routes"]["add"] == "add_salarycomponent"
    assert schema["routes"]["change"] == "change_salarycomponent"
    assert schema["routes"]["view"] == "view_salarycomponent"


def test_pagination_is_present_and_typed(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-pagination-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    assert isinstance(schema["pagination"]["page_size"], int)
    assert isinstance(schema["pagination"]["page_size_options"], list)
    assert schema["pagination"]["enabled"] is True


def test_pdf_config_present_without_explicit_configuration(bootstrap_tenant):
    """SalaryComponent has no RESAAS.pdf override - the schema must still
    come back with sane defaults, not an empty/missing block."""
    tenant = bootstrap_tenant("schema-pdf-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    assert schema["pdf"]["enabled"] is True
    assert schema["pdf"]["detail_endpoint"] == "hr/salarycomponents/{id}/pdf/"


# =========================================================
# FIELDS - real Django field introspection (_schema_fields)
# =========================================================

def test_char_field_metadata(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-field-char-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    name_field = _field(schema, "name")
    assert name_field["type"] == "CharField"
    assert name_field["required"] is True
    assert name_field["max_length"] == 150


def test_choice_field_metadata(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-field-choice-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    component_type = _field(schema, "component_type")
    assert component_type["choices"] == [
        ["earning", "Earning"], ["deduction", "Deduction"],
    ]


def test_decimal_field_metadata(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-field-decimal-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    amount = _field(schema, "amount")
    assert amount["type"] == "DecimalField"


def test_boolean_field_metadata(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-field-boolean-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    is_taxable = _field(schema, "is_taxable")
    assert is_taxable["type"] == "BooleanField"
    # required is derived purely from the model field's own `blank`
    # (not from having a `default=`) - is_taxable has neither blank=True
    # nor null=True, so it comes back required, same as any other field
    assert is_taxable["required"] is True


def test_foreign_key_field_metadata(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-field-fk-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "Attendance")

    employee = _field(schema, "employee")
    assert employee["type"] == "ForeignKey"
    assert employee["relation"] == "hr.Employee"


def test_date_and_datetime_field_metadata(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-field-date-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "Attendance")

    assert _field(schema, "date")["type"] == "DateField"
    assert _field(schema, "check_in")["type"] == "DateTimeField"


def test_integer_field_metadata(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-field-integer-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "Attendance")

    assert _field(schema, "late_minutes")["type"] == "IntegerField"


# =========================================================
# ACTIONS - decorator -> ActionSyncService -> schema, over HTTP
# =========================================================

class _ViewWithConfirmAction(ModelViewSet):
    from dev.demo.models import Product
    from dev.demo.serializers import ProductSerializer

    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @resaas_action(
        detail=True, methods=["post"], label="Confirm",
        icon="mdi-check", tooltip="Confirm this record",
        position="top", order=5, visible=True, autorequest=True,
    )
    def confirm(self, request, pk=None):
        ...


def test_actions_reach_the_schema_with_full_metadata(bootstrap_tenant):
    ActionSyncService.sync_view(_ViewWithConfirmAction)

    tenant = bootstrap_tenant("schema-actions-tenant", modules=("demo",))
    schema = _schema(tenant["client"], "demo", "Product")

    action = next(a for a in schema["actions"] if a["action"] == "confirm")

    assert action["label"] == "Confirm"
    assert action["icon"] == "mdi-check"
    assert action["tooltip"] == "Confirm this record"
    assert action["position"] == "top"
    assert action["order"] == 5
    assert action["visible"] is True
    assert action["autorequest"] is True
    assert action["method"] == "POST"
    assert action["methods"] == ["POST"]
    assert action["url"] == "confirm"
    assert action["endpoint"] == "demo/products/{id}/confirm/"
    assert action["permission"] == "confirm_product"


def test_detail_and_details_are_both_present_and_consistent(bootstrap_tenant):
    ActionSyncService.sync_view(_ViewWithConfirmAction)

    tenant = bootstrap_tenant("schema-detail-tenant", modules=("demo",))
    schema = _schema(tenant["client"], "demo", "Product")

    action = next(a for a in schema["actions"] if a["action"] == "confirm")

    assert action["detail"] is True
    assert action["details"] is True
    assert action["detail"] == action["details"]
