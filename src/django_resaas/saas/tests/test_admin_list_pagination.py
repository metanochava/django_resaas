"""File/App/Group/Translation (auth/permissions/ is covered separately by
test_permission_list.py) all used to bypass pagination entirely (either a
custom list() overriding self._paginator, or pagination_class = None),
returning every row as a bare array. That is what the new list_file/
list_translation/list_app frontend pages, and the existing list_group
page, would otherwise show unpaginated on big tables. Now all four use
the platform's standard ResaasPagination (same as any other proper
RESAAS CRUD endpoint).

Also covers a real, independent bug found while wiring up FileSEPage.vue:
FileAPIView.create() read entity_id from a one-off "E" request header
that no frontend code ever sent, so every file upload failed with
ENTITY_NOT_PROVIDED - it now uses the standard tenant context
(request.entity_id, set by the tenant middleware from X-RESAAS-Context)
like every other tenant-scoped view.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from django_resaas.saas.models.app import App
from django_resaas.saas.models.file import File
from django_resaas.saas.models.group import Group
from django_resaas.saas.models.language import Language
from django_resaas.saas.models.translation import Translation

pytestmark = pytest.mark.django_db


def test_file_list_is_paginated(bootstrap_tenant, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    tenant = bootstrap_tenant("file-list")

    for i in range(12):
        File.objects.create(
            entity=tenant["entity"],
            file=SimpleUploadedFile(f"f{i}.txt", b"x"),
            size=1,
        )

    response = tenant["client"].get("/api/django_resaas/files/")

    assert response.status_code == 200
    assert response.data["count"] == 12
    assert len(response.data["results"]) == 10


def test_file_create_uses_tenant_context_not_a_custom_header(
    bootstrap_tenant, settings, tmp_path, monkeypatch
):
    settings.MEDIA_ROOT = tmp_path
    tenant = bootstrap_tenant("file-create")

    # DiskManegarService.freeSpace()/recoverSpace() are called here and
    # in destroy(), but were never actually implemented on
    # DiskManegarService (see its own get_entity_usage() docstring) -
    # a separate, pre-existing gap this test isn't about. Stub it out
    # to isolate the entity_id fix under test.
    from django_resaas.saas.core.services.disc_manager import DiskManegarService
    monkeypatch.setattr(
        DiskManegarService, "freeSpace",
        staticmethod(lambda *a, **k: True), raising=False,
    )

    upload = SimpleUploadedFile("photo.jpg", b"fake-bytes", content_type="image/jpeg")
    response = tenant["client"].post(
        "/api/django_resaas/files/", {"file": upload}, format="multipart"
    )

    assert response.status_code == 201, response.data
    created = File.objects.get(id=response.data["id"])
    assert created.entity_id == tenant["entity"].id


def test_app_list_is_paginated(bootstrap_tenant):
    tenant = bootstrap_tenant("app-list")

    for i in range(12):
        App.objects.create(name=f"app{i}")

    response = tenant["client"].get("/api/django_resaas/apps/")

    assert response.status_code == 200
    assert response.data["count"] >= 12
    assert len(response.data["results"]) == 10


def test_branch_list_is_paginated_and_supports_page_size_zero(bootstrap_tenant):
    from django_resaas.saas.models.branch import Branch

    tenant = bootstrap_tenant("branch-list")

    for i in range(12):
        Branch.objects.create(name=f"branch{i}", entity=tenant["entity"])

    response = tenant["client"].get("/api/django_resaas/branchs/")

    assert response.status_code == 200
    # +1 for bootstrap_tenant's own "Main" branch.
    assert response.data["count"] >= 13
    assert len(response.data["results"]) == 10

    # UserBranchesPanel.vue needs the full list in one go to render its
    # checkbox picker, same as the other page_size=0 consumers already
    # covered by test_permission_list.py.
    all_response = tenant["client"].get(
        "/api/django_resaas/branchs/", {"page_size": 0}
    )

    assert all_response.status_code == 200
    assert len(all_response.data["results"]) == all_response.data["count"] >= 13


def test_group_list_is_paginated(bootstrap_tenant):
    tenant = bootstrap_tenant("group-list")

    for i in range(12):
        Group.objects.get_or_create(name=f"group{i}")

    response = tenant["client"].get("/api/auth/groups/")

    assert response.status_code == 200
    assert response.data["count"] >= 12
    assert len(response.data["results"]) == 10


def test_translation_list_serves_translation_rows_and_is_paginated(bootstrap_tenant):
    tenant = bootstrap_tenant("translation-list")
    language = Language.objects.create(name="Português", code="pt-pt")

    for i in range(12):
        Translation.objects.create(
            language=language, chave=f"Key {i}", translation=f"Valor {i}"
        )

    response = tenant["client"].get("/api/django_resaas/translations/")

    assert response.status_code == 200
    assert response.data["count"] == 12
    assert len(response.data["results"]) == 10
    # Was serving Language rows (a copy-paste bug) - a Translation row
    # has 'chave'/'translation', a Language row never does.
    assert "chave" in response.data["results"][0]
