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

from django_resaas.saas.core.decorators.action import resaas_action
from django_resaas.saas.core.services.action_sync_service import ActionSyncService

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


def test_model_endpoint_honors_a_resaas_override(bootstrap_tenant):
    """NotificationPreferenceAPIView registers itself with an explicit
    @register_view("preferences", module="notifications") name instead
    of the default (module + model_name + "s") - the schema's default
    endpoint guess (notifications/notificationpreferences/) 404s, so
    the model declares RESAAS.endpoint to override it (see
    notifications/models/preference.py)."""
    tenant = bootstrap_tenant("schema-endpoint-override-tenant", modules=("notifications",))
    schema = _schema(tenant["client"], "notifications", "NotificationPreference")

    assert schema["model"]["endpoint"] == "notifications/preferences/"


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


def test_field_readonly_defaults_to_false(bootstrap_tenant):
    """SalaryComponent declares no RESAAS.fields read_only override and
    every one of its fields stays editable=True (the Django default) -
    every field must still come back with an explicit read_only key,
    not a missing one, same as required always being present."""
    tenant = bootstrap_tenant("schema-field-readonly-default-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    name_field = _field(schema, "name")
    assert name_field["read_only"] is False


def test_field_readonly_override_and_required_interaction(bootstrap_tenant):
    """User.RESAAS.fields declares password/email/mobile read_only - a
    field a user can never fill in from this form (password/email/
    mobile can only ever be changed by their own owner - UserSerializer
    enforces this server-side) must not also carry a blocking
    'required' validation rule the user has no way to satisfy."""
    tenant = bootstrap_tenant("schema-field-readonly-tenant")
    schema = _schema(tenant["client"], "django_resaas", "User")

    email_field = _field(schema, "email")
    assert email_field["read_only"] is True
    assert email_field["required"] is False  # blank=True on the model field
    assert all(r["type"] != "required" for r in email_field.get("rules", []))

    password_field = _field(schema, "password")
    assert password_field["read_only"] is True
    assert password_field["required"] is True  # blank=False on the model field
    # read_only wins - required alone would otherwise block submission
    # over a field this form can never actually set.
    assert all(r["type"] != "required" for r in password_field.get("rules", []))

    # profile has its own RESAAS.fields entry (accept/max_size/multiple)
    # but no read_only override - confirms the two configs are independent.
    profile_field = _field(schema, "profile")
    assert profile_field["read_only"] is False


def test_field_readonly_derived_from_editable_false(bootstrap_tenant):
    """id/entity/branch are declared editable=False on SoftBaseModel/
    BaseModel (they're auto-set by the tenant middleware/perform_create,
    never something a user fills in) - the schema must mark them
    read_only automatically, the same way DRF's own ModelSerializer
    would, without needing a RESAAS.fields override for every single
    model that inherits these base fields."""
    tenant = bootstrap_tenant("schema-field-editable-false-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    id_field = _field(schema, "id")
    assert id_field["read_only"] is True


def test_field_write_only_and_allow_null_and_default(bootstrap_tenant):
    """write_only/allow_null/default are plain, always-present schema
    keys (write_only via RESAAS.fields override, allow_null from the
    model field's own `null`, default from the model field's own
    `default`) - same "always explicit, never missing" contract as
    required/read_only."""
    tenant = bootstrap_tenant("schema-field-write-only-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    name_field = _field(schema, "name")
    assert name_field["write_only"] is False
    assert name_field["allow_null"] is False

    is_taxable = _field(schema, "is_taxable")
    # BooleanField with a default=True/False still reports its default
    # back (used by the frontend to prefill a brand-new record's form -
    # base_store.js's resetForm()).
    assert "default" in is_taxable


def test_file_and_image_fields_forward_multiple_and_max_size(bootstrap_tenant):
    """User.RESAAS.fields.profile already declared accept/max_size/
    multiple (saas/models/user.py) but _resolve_ui() only ever forwarded
    `accept` into props - multiple/max_size existed in the config dict
    and were silently dropped. Also: ImageField resolved to component
    "s-image", which was never an actual registered component (only
    s-upload/s-file - see boot/components.js) - every ImageField in any
    schema pointed at a component Vue could never resolve."""
    tenant = bootstrap_tenant("schema-file-multiple-tenant")
    schema = _schema(tenant["client"], "django_resaas", "User")

    profile_field = _field(schema, "profile")
    assert profile_field["component"] == "s-file"
    assert profile_field["props"]["accept"] == ".png,.jpg,.jpeg,.webp"
    assert profile_field["props"]["multiple"] is False
    assert profile_field["props"]["maxSize"] == 2 * 1024 * 1024


def test_choice_field_metadata(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-field-choice-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    component_type = _field(schema, "component_type")
    assert component_type["choices"] == [
        ["earning", "Earning"],
        ["deduction", "Deduction"],
        # Fase 8 (Payroll): Employer Contribution - see
        # hr/models/salary_component.py.
        ["employer_contribution", "Employer Contribution"],
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


def test_relation_field_carries_relation_config(bootstrap_tenant):
    """A ForeignKey/OneToOneField/ManyToManyField must come back with
    everything a generic s-select/s-multiselect needs to offer a
    Django-Admin-style "add related" button: which model to build a
    create form for, its real endpoint (RESAAS.endpoint-aware, not a
    re-guessed convention), and the add/change/view permission
    codenames the frontend already knows how to check via
    User.can()."""
    tenant = bootstrap_tenant("schema-relation-config-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "Attendance")

    employee = _field(schema, "employee")
    assert employee["relation_config"] == {
        "app": "hr",
        "model": "Employee",
        "endpoint": "hr/employees/",
        "permissions": {
            "add": "add_employee",
            "change": "change_employee",
            "view": "view_employee",
        },
    }


def test_non_relation_field_has_no_relation_config(bootstrap_tenant):
    tenant = bootstrap_tenant("schema-no-relation-config-tenant", modules=("hr",))
    schema = _schema(tenant["client"], "hr", "SalaryComponent")

    name_field = _field(schema, "name")
    assert "relation_config" not in name_field


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
