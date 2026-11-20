"""Printing (core/printing): documents registered by modules, the PDF on a
paper format, the Branch's printers and their default documents."""
import pytest
from rest_framework.test import APIClient

from django_resaas.saas.core import printing
from django_resaas.saas.core.printing.render import content_height_mm, page_css
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.printer import Printer

pytestmark = pytest.mark.django_db

CODE = "django_resaas.test_branch_card"


@pytest.fixture(autouse=True)
def test_document():
    printing.register({
        "code": CODE,
        "label": "Branch card",
        "permission": "view_branch",
        "template": "django_resaas/print/test_document.html",
        "formats": ["thermal_80", "a4"],
        "default_format": "thermal_80",
        # the request's own Branches only (tenant scope)
        "queryset": lambda request: Branch.objects.filter(entity_id=request.entity_id),
        "context": lambda request, obj, paper: {"lines": [obj.name] * 3},
        "title": lambda obj: f"Branch card {obj.name}",
    })
    yield
    printing.unregister(CODE)


def _pdf(client, obj_id, **params):
    return client.get(f"/api/printing/{CODE}/{obj_id}/pdf/", params)


def test_registry_ignores_a_document_with_an_unknown_format():
    assert printing.register({"code": "x.bad", "label": "Bad", "permission": "view_branch", "template": "t.html",
                              "formats": ["letter"], "queryset": None, "context": None}) is None
    assert printing.get("x.bad") is None


def test_the_document_prints_on_each_of_its_papers(bootstrap_tenant):
    tenant = bootstrap_tenant("print-pdf")

    for paper in ("thermal_80", "a4"):
        response = _pdf(tenant["client"], tenant["branch"].id, paper=paper)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response.content[:4] == b"%PDF"


def test_a_thermal_roll_is_as_long_as_its_content():
    css = page_css(printing.PAPER_FORMATS["thermal_80"], 123.4)
    assert "size: 80mm 123.4mm" in css
    short = content_height_mm("django_resaas/print/test_document.html",
                              {"paper": printing.PAPER_FORMATS["thermal_80"], "lines": ["a"],
                               "document": {"label": "X"}, "page_css": page_css(printing.PAPER_FORMATS["thermal_80"])})
    long = content_height_mm("django_resaas/print/test_document.html",
                             {"paper": printing.PAPER_FORMATS["thermal_80"], "lines": ["a"] * 40,
                              "document": {"label": "X"}, "page_css": page_css(printing.PAPER_FORMATS["thermal_80"])})
    assert 0 < short < long < 3000


def test_a_paper_the_document_does_not_support_is_a_400(bootstrap_tenant):
    tenant = bootstrap_tenant("print-paper")

    response = _pdf(tenant["client"], tenant["branch"].id, paper="a6")

    assert response.status_code == 400 and response.data["error"]["code"] == "paper_not_available"


def test_another_entitys_object_is_a_404(bootstrap_tenant):
    mine = bootstrap_tenant("print-scope-a")
    theirs = bootstrap_tenant("print-scope-b")

    response = _pdf(mine["client"], theirs["branch"].id)

    assert response.status_code == 404


def test_unknown_document_and_anonymous(bootstrap_tenant):
    tenant = bootstrap_tenant("print-unknown")

    assert tenant["client"].get(f"/api/printing/nope.doc/{tenant['branch'].id}/pdf/").status_code == 404
    assert APIClient().get(f"/api/printing/{CODE}/{tenant['branch'].id}/pdf/").status_code in (401, 403)


def test_without_the_permission_it_is_neither_listed_nor_printed(bootstrap_tenant, monkeypatch):
    tenant = bootstrap_tenant("print-perm")
    printing.register({**printing.get(CODE), "code": "django_resaas.secret", "permission": "no_such_permission"})
    try:
        listed = [row["code"] for row in tenant["client"].get("/api/printing/documents/").data["documents"]]
        assert CODE in listed and "django_resaas.secret" not in listed
        assert _pdf(tenant["client"].__class__(), tenant["branch"].id).status_code in (401, 403)
        response = tenant["client"].get(f"/api/printing/django_resaas.secret/{tenant['branch'].id}/pdf/")
        assert response.status_code == 403
    finally:
        printing.unregister("django_resaas.secret")


def test_a_documents_default_printer_is_unique_per_branch_and_sets_its_paper(bootstrap_tenant):
    tenant = bootstrap_tenant("print-printers")
    client = tenant["client"]

    first = client.post("/api/django_resaas/printers/", {"name": "Counter", "paper_format": "thermal_80",
                                                         "documents": [CODE]}, format="json")
    assert first.status_code in (200, 201, 202), first.data
    second = client.post("/api/django_resaas/printers/", {"name": "Office", "paper_format": "a4",
                                                          "documents": [CODE]}, format="json")
    assert second.status_code in (200, 201, 202), second.data

    # the newest default wins; the other printer no longer has it
    assert Printer.objects.get(name="Counter").documents == []
    row = next(r for r in client.get("/api/printing/documents/").data["documents"] if r["code"] == CODE)
    assert row["printer"]["name"] == "Office" and row["printer"]["paper_format"] == "a4"

    # without ?paper the PDF comes out on the default printer's paper
    assert _pdf(client, tenant["branch"].id).status_code == 200


def test_a_printer_cannot_take_a_document_its_paper_does_not_support(bootstrap_tenant):
    tenant = bootstrap_tenant("print-printer-bad")

    response = tenant["client"].post("/api/django_resaas/printers/", {"name": "Small", "paper_format": "a6",
                                                                      "documents": [CODE]}, format="json")

    assert response.status_code == 400


def test_a_new_models_permissions_reach_the_profiles_in_the_same_migrate(bootstrap_tenant):
    """create_core_profiles runs before the receivers that create permissions:
    it creates them first, so the Admin profile gets a new model's at once."""
    from django.apps import apps as django_apps
    from django.contrib.auth.models import Permission

    from django_resaas.saas.apps import create_core_profiles
    from django_resaas.saas.models.group import Group

    bootstrap_tenant("print-profiles")
    Permission.objects.filter(codename__endswith="_printer").delete()
    config = django_apps.get_app_config("django_resaas")

    create_core_profiles(sender=config, app_config=config, using="default")

    admin = Group.objects.get(name="Admin")
    assert set(admin.permissions.filter(codename__endswith="_printer").values_list("codename", flat=True)) == {
        "view_printer", "add_printer", "change_printer", "list_printer", "delete_printer"}


def test_a_document_may_carry_a_qr_code_and_a_barcode(bootstrap_tenant):
    from django_resaas.saas.core.printing.render import _codes

    document = {"qr": lambda request, obj: f"Branch {obj}", "barcode": lambda request, obj: "ABC123"}
    codes = _codes(None, document, "Main")

    assert codes["qr_value"] == "Branch Main" and codes["barcode_value"] == "ABC123"
    assert codes["qr_b64"] and codes["barcode_b64"]
    # a code that cannot be drawn is left out, the print goes on
    assert _codes(None, {"barcode": lambda request, obj: 1 / 0}, "x") == {}

    tenant = bootstrap_tenant("print-codes")
    printing.register({**printing.get(CODE), "qr": lambda request, obj: obj.name, "barcode": lambda request, obj: "B1"})
    assert _pdf(tenant["client"], tenant["branch"].id).status_code == 200


def _verifiable(**extra):
    return {**printing.get(CODE), "code": "django_resaas.verifiable_branch",
            "verify": lambda obj: {"Branch": obj.name, "Status": "Open", "__voided__": obj.name == "Closed"},
            "verify_queryset": lambda: Branch.objects.all(), **extra}


def test_a_verifiable_documents_qr_is_its_verification_link(bootstrap_tenant, settings):
    from django_resaas.saas.core.printing.render import _codes
    from django_resaas.saas.core.printing.verify import read_token

    settings.RESAAS_VERIFY_URL = "https://app.example.com/"
    tenant = bootstrap_tenant("print-verify-qr")
    document = _verifiable()

    url = _codes(None, document, tenant["branch"])["qr_value"]

    assert url.startswith("https://app.example.com/#/v/")
    assert read_token(url.rsplit("/", 1)[1]) == ("django_resaas.verifiable_branch", str(tenant["branch"].id))


def test_the_public_page_shows_only_the_public_fields(bootstrap_tenant):
    from rest_framework.test import APIClient

    from django_resaas.saas.core.printing.verify import make_token

    tenant = bootstrap_tenant("print-verify")
    printing.register(_verifiable())
    try:
        token = make_token("django_resaas.verifiable_branch", tenant["branch"])
        anonymous = APIClient()

        response = anonymous.get(f"/api/printing/verify/{token}/")
        assert response.status_code == 200
        assert response.data["entity"] == tenant["entity"].name
        assert {"label": "Branch", "value": tenant["branch"].name} in response.data["fields"]
        assert response.data["voided"] is False
        assert all(row["label"] != "__voided__" for row in response.data["fields"])

        # an altered token, or one of a document that cannot be verified: the same 404
        assert anonymous.get(f"/api/printing/verify/{token[:-2]}xx/").status_code == 404
        other = make_token(CODE, tenant["branch"])
        assert anonymous.get(f"/api/printing/verify/{other}/").status_code == 404
        # the record is gone
        gone = make_token("django_resaas.verifiable_branch", type("X", (), {"pk": "00000000-0000-0000-0000-000000000000"})())
        assert anonymous.get(f"/api/printing/verify/{gone}/").status_code == 404
    finally:
        printing.unregister("django_resaas.verifiable_branch")
