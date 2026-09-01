"""
Locks the exact shape of `ResaasSchemaBuilder.build()` - the "Schema 1.0"
contract served to frontend consumers (quasar_resaas in particular).

See docs/api/schema-contract.md for the documented, versioned shape these
tests protect. Any change to this output is a contract change: bump
`ResaasSchemaBuilder.SCHEMA_VERSION` and update the docs alongside the test.
"""
import pytest

from django_resaas.core.schema.builder import ResaasSchemaBuilder
from django_resaas.models.address import Address
from django_resaas.models.group import Group
from django_resaas.models.model_extra_action import ModelExtraAction

pytestmark = pytest.mark.django_db


# =============================================================
# MODEL / ROUTES / SCHEMA_VERSION
# =============================================================

def test_plain_model_without_resaas_class():
    """A model with no `RESAAS` class still gets full, defaulted output."""
    builder = ResaasSchemaBuilder(
        Model=Group,
        fields=[{"name": "name"}, {"name": "editable"}],
    )
    schema = builder.build()

    assert schema["schema_version"] == "1.0"

    assert schema["model"] == {
        "app": "django_resaas",
        "name": "group",
        "class_name": "Group",
        "label": "Group",
        "label_plural": "Groups",
        "pk": "id",
        "endpoint": "django_resaas/groups/",
    }

    # no RESAAS class -> the framework's own convention-based defaults
    assert schema["routes"] == {
        "list": "list_group",
        "add": "add_group",
        "change": "change_group",
        "view": "view_group",
    }
    assert schema["ui"]["crud"] is True
    assert schema["filters"]["fields"] == ["name", "editable"]

    # backward-compatibility aliases
    assert schema["module"] == "django_resaas"
    assert schema["config"] == {"crud": True, "routes": schema["routes"]}


def test_model_with_custom_routes_overrides_defaults():
    """`RESAAS.routes` overrides the convention-based defaults per key."""
    builder = ResaasSchemaBuilder(Model=Address, fields=[])
    schema = builder.build()

    assert schema["routes"] == {
        "list": "add_address",
        "add": "add_address",
        "change": "change_address",
        "view": "view_address",
    }


def test_full_resaas_config_overrides_ui_filters_pagination_pdf(monkeypatch):
    """A `RESAAS` class overriding ui/filters/pagination/pdf is merged over
    the defaults key-by-key, not replaced wholesale."""

    class FullResaasConfig:
        label_field = "name"
        crud = False
        icon = "mdi-group"
        search_fields = ["name"]
        ui = {"dense": False, "show_pdf": False}
        filters = {"search": False}
        pagination = {"page_size": 25}
        pdf = {"enabled": False}
        routes = {"list": "custom_list_route"}

    monkeypatch.setattr(Group, "RESAAS", FullResaasConfig, raising=False)

    builder = ResaasSchemaBuilder(Model=Group, fields=[{"name": "name"}])
    schema = builder.build()

    # explicit overrides took effect...
    assert schema["ui"]["dense"] is False
    assert schema["ui"]["show_pdf"] is False
    assert schema["filters"]["search"] is False
    assert schema["pagination"]["page_size"] == 25
    assert schema["pdf"]["enabled"] is False
    assert schema["routes"]["list"] == "custom_list_route"

    # ...but unspecified keys keep their defaults (merge, not replace)
    assert schema["ui"]["crud"] is False  # from RESAAS.crud, not ui dict
    assert schema["ui"]["striped"] is True
    assert schema["filters"]["search_fields"] == ["name"]
    assert schema["pagination"]["default_ordering"] == "-id"
    assert schema["pdf"]["detail"] is True
    assert schema["routes"]["add"] == "add_group"
    assert schema["ui"]["icon"] == "mdi-group"


# =============================================================
# ACTIONS / PERMISSIONS (ModelExtraAction-backed)
# =============================================================

def test_custom_actions_and_permissions():
    ModelExtraAction.objects.create(
        app="django_resaas",
        model="group",
        action="export",
        label="Export",
        icon="mdi-download",
        method="GET",
        details=False,
        url="export",
        permission="export_group",
        order=1,
    )
    ModelExtraAction.objects.create(
        app="django_resaas",
        model="group",
        action="archive",
        label="Archive",
        method="POST",
        details=True,
        permission="archive_group",
        order=0,
    )

    builder = ResaasSchemaBuilder(Model=Group, fields=[])
    schema = builder.build()

    # ordered by (order, action) -> archive (order=0) before export (order=1)
    actions = schema["actions"]
    assert [a["action"] for a in actions] == ["archive", "export"]

    archive = actions[0]
    assert archive["endpoint"] == "django_resaas/groups/{id}/archive/"
    assert archive["permission"] == "archive_group"

    export = actions[1]
    assert export["endpoint"] == "django_resaas/groups/export/"
    assert export["permission"] == "export_group"

    assert schema["permissions"]["custom"] == {
        "export": "export_group",
        "archive": "archive_group",
    }

    # default CRUD permission names always present alongside custom ones
    assert schema["permissions"]["list"] == "list_group"
    assert schema["permissions"]["delete"] == "delete_group"


def test_no_custom_actions_yields_empty_actions_and_custom_permissions():
    builder = ResaasSchemaBuilder(Model=Group, fields=[])
    schema = builder.build()

    assert schema["actions"] == []
    assert schema["permissions"]["custom"] == {}


def test_action_method_is_the_single_primary_method_not_a_joined_string():
    """
    `ModelExtraAction.method` is comma-joined when a `@resaas_action`
    declares more than one HTTP method - the schema must resolve that to
    one unambiguous "method" for the UI to submit with (the first
    declared one), rather than making every consumer split/guess it.
    The full list stays available under "methods".
    """
    ModelExtraAction.objects.create(
        app="django_resaas",
        model="group",
        action="upsert",
        label="Upsert",
        method="POST,PUT",
        details=True,
        permission="upsert_group",
    )

    builder = ResaasSchemaBuilder(Model=Group, fields=[])
    action = builder.build()["actions"][0]

    assert action["method"] == "POST"
    assert action["methods"] == ["POST", "PUT"]


def test_action_exposes_both_detail_and_details_with_the_same_value():
    """
    "detail" is the conceptual/API name going forward (matches DRF's own
    `detail=` kwarg); "details" is preserved alongside it since the DB
    field and existing frontend code depend on it. Both must always
    agree - see docs/api/schema-contract.md.
    """
    ModelExtraAction.objects.create(
        app="django_resaas",
        model="group",
        action="archive",
        label="Archive",
        method="POST",
        details=True,
        permission="archive_group",
    )

    builder = ResaasSchemaBuilder(Model=Group, fields=[])
    action = builder.build()["actions"][0]

    assert action["detail"] is True
    assert action["details"] is True


def test_action_method_defaults_to_post_when_unset():
    ModelExtraAction.objects.create(
        app="django_resaas",
        model="group",
        action="ping",
        label="Ping",
        method="",
        details=False,
        permission="ping_group",
    )

    builder = ResaasSchemaBuilder(Model=Group, fields=[])
    action = builder.build()["actions"][0]

    assert action["method"] == "POST"
    assert action["methods"] == []
