"""Tenant scope and per-action authorization of the core plain ViewSets that
used to require only authentication (ExplicitAccessMixin): BranchUser, File,
Branch, and the global catalogues (ContentType "models", Translation,
Language, LayoutSetting).

Pattern under test (core/base/access.py ActionPermissionMixin):
reads are scoped (tenant objects) or open to any authenticated caller
(global catalogues); every write needs its permission in the signed
context; undeclared actions are denied. See also
test_branch_user_group_tenant_scope.py.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from django_resaas.saas.core.tenant.context import ResaasContextService
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.file import File
from django_resaas.saas.models.group import Group
from django_resaas.saas.models.language import Language
from django_resaas.saas.models.layout_setting import LayoutSetting
from django_resaas.saas.models.translation import Translation

pytestmark = pytest.mark.django_db

API = "/api/django_resaas"


def _rows(response):
    data = response.json()
    return data["results"] if isinstance(data, dict) and "results" in data else data


def _ids(response):
    return {str(row["id"]) for row in _rows(response)}


@pytest.fixture
def tenants(bootstrap_tenant):
    a = bootstrap_tenant("core-scope-a")
    b = bootstrap_tenant("core-scope-b")

    # a member of A acting with a profile that holds no permission
    member = get_user_model().objects.create_user(
        username="core-scope-a-member", email="core-scope-a-member@example.com", password="pass-12345",
    )
    EntityUser.objects.create(entity=a["entity"], user=member, state="Active")
    a["member_branch_user"] = BranchUser.objects.create(branch=a["branch"], user=member, state="Active")
    plain = Group.objects.create(name="Core Scope Plain")
    EntityGroup.objects.create(entity=a["entity"], group=plain, state="Active")
    BranchUserGroup.objects.create(branch=a["branch"], user=member, group=plain, state="Active")

    context = ResaasContextService.issue(user=member, entity_id=a["entity"].id, branch_id=a["branch"].id, group_id=plain.id)
    a["plain_client"] = APIClient()
    a["plain_client"].force_authenticate(user=member)
    a["plain_client"].credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")
    a["member"] = member

    b["branch_user"] = BranchUser.objects.get(branch=b["branch"], user=b["user"])
    return a, b


class TestBranchUser:
    def test_list_is_scoped_to_current_branch(self, tenants):
        a, b = tenants
        ids = _ids(a["client"].get(f"{API}/branchusers/"))

        assert str(a["member_branch_user"].id) in ids
        assert str(b["branch_user"].id) not in ids

    def test_other_entity_row_is_not_found(self, tenants):
        a, b = tenants
        url = f"{API}/branchusers/{b['branch_user'].id}/"

        assert a["client"].get(url).status_code == 404
        assert a["client"].patch(url, {"user": a["user"].id}, format="json").status_code == 404
        assert a["client"].delete(url).status_code == 404

        b["branch_user"].refresh_from_db()
        assert b["branch_user"].user_id == b["user"].id

    def test_cannot_give_branch_access_to_other_entity_user(self, tenants):
        a, b = tenants
        before = BranchUser.objects.count()

        response = a["client"].post(f"{API}/branchusers/", {"user": b["user"].id})

        assert response.status_code == 400
        assert "user" in response.json()["error"]["details"]
        assert BranchUser.objects.count() == before

    def test_create_takes_branch_from_context(self, tenants):
        a, _ = tenants
        newcomer = get_user_model().objects.create_user(username="core-scope-new", email="n@example.com", password="pass-12345")
        EntityUser.objects.create(entity=a["entity"], user=newcomer, state="Active")
        other_branch = Branch.objects.create(name="Elsewhere", entity=a["entity"])

        response = a["client"].post(f"{API}/branchusers/", {"user": newcomer.id, "branch": other_branch.id})

        assert response.status_code == 201
        assert BranchUser.objects.get(user=newcomer).branch_id == a["branch"].id

    def test_without_permission_is_forbidden(self, tenants):
        a, _ = tenants
        assert a["plain_client"].get(f"{API}/branchusers/").status_code == 403
        assert a["plain_client"].delete(f"{API}/branchusers/{a['member_branch_user'].id}/").status_code == 403
        assert BranchUser.objects.filter(pk=a["member_branch_user"].id).exists()


class TestFile:
    @pytest.fixture
    def files(self, tenants):
        a, b = tenants
        return (
            File.objects.create(entity=a["entity"], model="test", size=1),
            File.objects.create(entity=b["entity"], model="test", size=1),
        )

    def test_list_is_scoped_to_current_entity(self, tenants, files):
        a, _ = tenants
        file_a, file_b = files
        ids = _ids(a["client"].get(f"{API}/files/"))

        assert str(file_a.id) in ids
        assert str(file_b.id) not in ids

    def test_other_entity_file_is_not_found(self, tenants, files):
        a, _ = tenants
        _, file_b = files
        url = f"{API}/files/{file_b.id}/"

        assert a["client"].get(url).status_code == 404
        assert a["client"].patch(url, {"model": "hacked"}, format="json").status_code == 404
        a["client"].delete(url)

        file_b.refresh_from_db()
        assert file_b.model == "test"

    def test_por_entity_ignores_another_entity_id(self, tenants, files):
        a, b = tenants
        response = a["client"].get(f"{API}/files/por_entity/", {"entity": b["entity"].id})

        assert response.status_code == 200
        assert response.json() == []


class TestBranch:
    def test_other_entity_branch_is_not_found(self, tenants):
        a, b = tenants
        url = f"{API}/branchs/{b['branch'].id}/"

        assert a["client"].get(url).status_code == 404
        assert a["client"].patch(url, {"name": "Hacked"}, format="json").status_code == 404
        assert a["client"].get(f"{url}Url/").status_code == 404

        b["branch"].refresh_from_db()
        assert b["branch"].name == "Main"

    def test_member_without_permission_cannot_change_or_delete(self, tenants):
        a, _ = tenants
        url = f"{API}/branchs/{a['branch'].id}/"

        assert a["plain_client"].patch(url, {"name": "Renamed"}, format="json").status_code == 403
        assert a["plain_client"].delete(url).status_code == 403

        a["branch"].refresh_from_db()
        assert a["branch"].name == "Main"

    def test_member_can_still_read_own_entity_branches(self, tenants):
        a, _ = tenants
        response = a["plain_client"].get(f"{API}/branchs/")

        assert response.status_code == 200
        assert str(a["branch"].id) in _ids(response)

    def test_admin_can_still_rename(self, tenants):
        a, _ = tenants
        response = a["client"].patch(f"{API}/branchs/{a['branch'].id}/", {"name": "Head Office"}, format="json")

        assert response.status_code == 200
        a["branch"].refresh_from_db()
        assert a["branch"].name == "Head Office"


class TestGlobalCatalogues:
    def test_content_types_are_read_only(self, tenants):
        a, _ = tenants
        content_type = ContentType.objects.get_for_model(Language)
        count = ContentType.objects.count()

        assert a["plain_client"].get(f"{API}/models/").status_code == 200
        # not even the Root caller may write the ContentType catalogue
        assert a["client"].delete(f"{API}/models/{content_type.id}/").status_code == 403
        assert a["client"].post(f"{API}/models/", {"app_label": "x", "model": "y"}).status_code == 403
        assert ContentType.objects.count() == count

    def test_translations_read_for_members_write_needs_permission(self, tenants):
        a, _ = tenants
        language = Language.objects.create(name="Testish", code="te-st")
        row = Translation.objects.create(language=language, chave="Save", translation="Gravar")
        url = f"{API}/translations/{row.id}/"

        assert a["plain_client"].get(f"{API}/translations/").status_code == 200
        assert a["plain_client"].patch(url, {"translation": "Defaced"}, format="json").status_code == 403
        assert a["plain_client"].delete(url).status_code == 403
        assert a["plain_client"].post(f"{API}/translations/", {"language": language.id, "chave": "X", "translation": "Y"}).status_code == 403

        row.refresh_from_db()
        assert row.translation == "Gravar"

        # Root holds change_translation
        assert a["client"].patch(url, {"translation": "Guardar"}, format="json").status_code == 200

    def test_languages_reads_public_writes_need_permission(self, tenants):
        a, _ = tenants
        language = Language.objects.create(name="Testish", code="te-st")
        url = f"{API}/languages/{language.id}/"

        assert APIClient().get(f"{API}/languages/").status_code == 200
        assert a["plain_client"].delete(url).status_code == 403
        assert a["plain_client"].patch(url, {"name": "Defaced"}, format="json").status_code == 403
        assert APIClient().delete(url).status_code == 401

        language.refresh_from_db()
        assert language.name == "Testish"

    def test_layout_settings_read_for_members_write_needs_permission(self, tenants):
        a, _ = tenants
        preset = LayoutSetting.objects.create(name="Preset")
        url = f"{API}/layoutsettings/{preset.id}/"

        assert a["plain_client"].get(f"{API}/layoutsettings/").status_code == 200
        assert a["plain_client"].patch(url, {"name": "Defaced"}, format="json").status_code == 403
        assert a["plain_client"].delete(url).status_code == 403

        preset.refresh_from_db()
        assert preset.name == "Preset"
