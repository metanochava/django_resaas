"""Export (CSV / PDF) and CSV import of a group's permissions
(auth/groups/{id}/permissions_csv|permissions_pdf|import_permissions)."""
import csv
import io

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.group import Group
from django_resaas.saas.tests.test_permission_api_security import _actor, _entity_group, _perms

pytestmark = pytest.mark.django_db

URL = "/api/auth/groups/"


def _csv_file(rows, header=("app", "codename")):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return SimpleUploadedFile("permissions.csv", buffer.getvalue().encode("utf-8"), content_type="text/csv")


def _import(client, group, rows, mode=None, header=("app", "codename")):
    data = {"file": _csv_file(rows, header)}
    if mode:
        data["mode"] = mode
    return client.post(f"{URL}{group.id}/import_permissions/", data, format="multipart")


def _codenames(group):
    return set(group.permissions.values_list("codename", flat=True))


def _parse(response):
    return list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))


# ------------------------------------------------------------------ export

def test_csv_lists_the_group_permissions(bootstrap_tenant):
    tenant = bootstrap_tenant("gpio-csv")
    client = _actor(tenant, "gpio-csv-actor", "view_group")
    group = _entity_group(tenant, "Nurse")
    group.permissions.set(_perms("view_group", "view_permission"))

    response = client.get(f"{URL}{group.id}/permissions_csv/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]
    rows = _parse(response)
    assert {r["codename"] for r in rows} == {"view_group", "view_permission"}
    assert set(rows[0]) == {"app", "model", "codename", "name"}


def test_csv_neutralises_formulas(bootstrap_tenant):
    tenant = bootstrap_tenant("gpio-formula")
    client = _actor(tenant, "gpio-formula-actor", "view_group")
    group = _entity_group(tenant, "Nurse")
    evil = Permission.objects.create(codename="x_evil", name='=HYPERLINK("http://x")',
                                     content_type=ContentType.objects.get_for_model(Group))
    group.permissions.add(evil)

    row = _parse(client.get(f"{URL}{group.id}/permissions_csv/"))[0]

    assert row["name"].startswith("'=")


def test_pdf_is_generated(bootstrap_tenant):
    tenant = bootstrap_tenant("gpio-pdf")
    client = _actor(tenant, "gpio-pdf-actor", "view_group")
    group = _entity_group(tenant, "Nurse")
    group.permissions.set(_perms("view_group"))

    response = client.get(f"{URL}{group.id}/permissions_pdf/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_export_needs_view_group_and_scope(bootstrap_tenant):
    mine = bootstrap_tenant("gpio-scope-a")
    theirs = bootstrap_tenant("gpio-scope-b")
    their_group = _entity_group(theirs, "Their Nurse")

    assert _actor(mine, "gpio-noperm").get(f"{URL}{their_group.id}/permissions_csv/").status_code == 403
    client = _actor(mine, "gpio-scope-actor", "view_group")
    assert client.get(f"{URL}{their_group.id}/permissions_csv/").status_code == 404
    assert client.get(f"{URL}{their_group.id}/permissions_pdf/").status_code == 404


# ------------------------------------------------------------------ import

def test_import_adds_by_default(bootstrap_tenant):
    tenant = bootstrap_tenant("gpio-add")
    client = _actor(tenant, "gpio-add-actor", "change_group", "view_group", "view_permission")
    group = _entity_group(tenant, "Nurse")
    group.permissions.set(_perms("view_group"))

    response = _import(client, group, [("auth", "view_permission")])

    assert response.status_code == 200, response.json()
    summary = response.json()
    # view_group exists for two models (RESAAS Group and auth.Group) - count
    # what the import changed, not the rows the group already had
    assert (summary["mode"], summary["added"], summary["removed"]) == ("add", 1, 0)
    assert _codenames(group) == {"view_group", "view_permission"}


def test_import_replace_makes_the_group_match_the_file(bootstrap_tenant):
    tenant = bootstrap_tenant("gpio-replace")
    client = _actor(tenant, "gpio-replace-actor", "change_group", "view_group", "view_permission")
    group = _entity_group(tenant, "Nurse")
    group.permissions.set(_perms("view_group"))

    response = _import(client, group, [("auth", "view_permission")], mode="replace")

    assert response.status_code == 200, response.json()
    assert _codenames(group) == {"view_permission"}
    assert response.json()["removed"] >= 1


def test_an_invalid_row_changes_nothing(bootstrap_tenant):
    tenant = bootstrap_tenant("gpio-invalid")
    client = _actor(tenant, "gpio-invalid-actor", "change_group", "view_group", "view_permission")
    group = _entity_group(tenant, "Nurse")

    response = _import(client, group, [("auth", "view_permission"), ("", "does_not_exist")])

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_rows"
    assert list(error["details"]["rows"]) == ["3"]
    assert _codenames(group) == set()


def test_an_ambiguous_codename_needs_the_app_column(bootstrap_tenant):
    tenant = bootstrap_tenant("gpio-ambiguous")
    client = _actor(tenant, "gpio-amb-actor", "change_group", "view_group")
    group = _entity_group(tenant, "Nurse")
    Permission.objects.create(codename="view_group", name="Other app view_group",
                              content_type=ContentType.objects.get_or_create(app_label="other_app", model="thing")[0])

    ambiguous = _import(client, group, [("", "view_group")])
    explicit = _import(client, group, [("django_resaas", "view_group")])

    assert ambiguous.status_code == 400
    assert explicit.status_code == 200, explicit.json()


def test_import_cannot_grant_what_the_caller_does_not_hold(bootstrap_tenant):
    tenant = bootstrap_tenant("gpio-escalate")
    client = _actor(tenant, "gpio-esc-actor", "change_group")
    group = _entity_group(tenant, "Nurse")

    response = _import(client, group, [("django_resaas", "delete_group")])

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_not_held"
    assert _codenames(group) == set()


def test_import_follows_the_group_change_rules(bootstrap_tenant):
    mine = bootstrap_tenant("gpio-shared-a")
    theirs = bootstrap_tenant("gpio-shared-b")
    client = _actor(mine, "gpio-shared-actor", "change_group", "view_group")
    shared = _entity_group(mine, "Shared")
    EntityGroup.objects.create(entity=theirs["entity"], group=shared, state="Active")

    assert _import(client, shared, [("django_resaas", "view_group")]).status_code == 403
    assert _import(_actor(mine, "gpio-view-only", "view_group"), _entity_group(mine, "Own"),
                   [("django_resaas", "view_group")]).status_code == 403


def test_bad_files_are_rejected(bootstrap_tenant):
    tenant = bootstrap_tenant("gpio-badfile")
    client = _actor(tenant, "gpio-bad-actor", "change_group", "view_group")
    group = _entity_group(tenant, "Nurse")

    no_file = client.post(f"{URL}{group.id}/import_permissions/", {}, format="multipart")
    no_column = _import(client, group, [("x",)], header=("permission",))
    bad_mode = _import(client, group, [("django_resaas", "view_group")], mode="merge")

    assert no_file.json()["error"]["code"] == "file_required"
    assert no_column.json()["error"]["code"] == "codename_column_missing"
    assert bad_mode.json()["error"]["code"] == "invalid_mode"


def test_exported_file_imports_back_unchanged(bootstrap_tenant):
    tenant = bootstrap_tenant("gpio-roundtrip")
    client = _actor(tenant, "gpio-rt-actor", "change_group", "view_group", "view_permission")
    group = _entity_group(tenant, "Nurse")
    group.permissions.set(_perms("view_group", "view_permission"))
    exported = client.get(f"{URL}{group.id}/permissions_csv/").content

    response = client.post(f"{URL}{group.id}/import_permissions/", {
        "file": SimpleUploadedFile("p.csv", exported, content_type="text/csv"), "mode": "replace",
    }, format="multipart")

    assert response.status_code == 200, response.json()
    assert response.json()["added"] == 0 and response.json()["removed"] == 0
    assert _codenames(group) == {"view_group", "view_permission"}
