"""The list PDF is the @resaas_action `pdf_list` (GET .../pdf_list/): its
permission is pdf_list_<model> - the codename the schema publishes
(permissions.pdf_list) and the frontend checks. Before 0.0.625 the function was
`pdflist` (URL .../pdflist/), so the backend required pdflist_<model> and
answered 403 to every group that held only pdf_list_<model>."""
import pytest

from django_resaas.saas.tests.test_permission_api_security import _actor

pytestmark = pytest.mark.django_db

URL = "/api/demo/members/pdf_list/"


def test_list_pdf_is_allowed_by_pdf_list_permission(bootstrap_tenant):
    tenant = bootstrap_tenant("perm-map-ok", modules=("demo",))
    client = _actor(tenant, "perm-map-ok-actor", "pdf_list_member")

    response = client.get(URL)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"


def test_list_pdf_is_not_allowed_by_the_old_pdflist_codename(bootstrap_tenant):
    """pdflist_<model> (created by the action sync before 0.0.625) no longer grants it."""
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    tenant = bootstrap_tenant("perm-map-name", modules=("demo",))
    from dev.demo.models import Member
    Permission.objects.get_or_create(
        codename="pdflist_member", content_type=ContentType.objects.get_for_model(Member),
        defaults={"name": "Can pdflist member"},
    )
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


def test_the_old_pdflist_url_is_gone(bootstrap_tenant):
    tenant = bootstrap_tenant("perm-map-old-url", modules=("demo",))

    assert tenant["client"].get("/api/demo/members/pdflist/").status_code == 404


def test_hooks_named_before_0_0_625_are_still_honoured():
    from django_resaas.saas.core.base.views import BaseAPIView

    class LegacyView(BaseAPIView):
        def get_pdflist_context(self, request, queryset):
            return {"legacy": True}

    with pytest.warns(DeprecationWarning, match="get_pdf_list_context"):
        hook = LegacyView()._legacy_pdf_hook("get_pdflist_context")

    assert hook(None, None) == {"legacy": True}
    assert BaseAPIView()._legacy_pdf_hook("get_pdflist_context") is None
