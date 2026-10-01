"""The list PDF (GET .../pdflist/) is the @resaas_action `pdf_list`: its
permission is pdf_list_<model> - the codename the schema publishes
(permissions.pdf_list) and the frontend checks. The function used to be
called `pdflist`, so the backend required pdflist_<model> and answered 403 to
every group that held only pdf_list_<model>."""
import pytest

from django_resaas.saas.tests.test_permission_api_security import _actor

pytestmark = pytest.mark.django_db

URL = "/api/demo/members/pdflist/"


def test_list_pdf_is_allowed_by_pdf_list_permission(bootstrap_tenant):
    tenant = bootstrap_tenant("perm-map-ok", modules=("demo",))
    client = _actor(tenant, "perm-map-ok-actor", "pdf_list_member")

    response = client.get(URL)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"


def test_list_pdf_is_not_allowed_by_the_old_pdflist_codename(bootstrap_tenant):
    tenant = bootstrap_tenant("perm-map-name", modules=("demo",))
    client = _actor(tenant, "perm-map-name-actor", "pdflist_member", "list_member")

    response = client.get(URL)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_list_pdf_without_permission_is_denied(bootstrap_tenant):
    tenant = bootstrap_tenant("perm-map-none", modules=("demo",))
    client = _actor(tenant, "perm-map-none-actor", "list_member")

    assert client.get(URL).status_code == 403


def test_the_schema_publishes_the_enforced_codename(bootstrap_tenant):
    tenant = bootstrap_tenant("perm-map-schema", modules=("demo",))

    schema = tenant["client"].get("/api/django_resaas/resaasapps/demo/member/schema/").json()

    assert schema["permissions"]["pdf_list"] == "pdf_list_member"
