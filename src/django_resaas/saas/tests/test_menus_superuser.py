"""UserAPIView.menus() - o menu deve reflectir sempre o grupo/perfil
actualmente seleccionado (BranchUserGroup), mesmo para superuser.

Antes desta correcção, `is_superuser` dava sempre todas as
permissões, ignorando por completo o grupo activo - trocar o perfil
para "Guest" (que BootstrapService já associa ao criador da entity,
para servir de pré-visualização) nunca alterava o menu de uma conta
superuser.
"""
import pytest

from django_resaas.saas.core.tenant.context import ResaasContextService
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.group import Group

pytestmark = pytest.mark.django_db


def _client_for_group(tenant, group):
    from rest_framework.test import APIClient

    BranchUserGroup.objects.get_or_create(
        user=tenant["user"], branch=tenant["branch"], group=group,
        defaults={"state": 1},
    )

    context = ResaasContextService.issue(
        user=tenant["user"], entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id, group_id=group.id,
    )

    client = APIClient()
    client.force_authenticate(user=tenant["user"])
    client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")
    return client


class TestMenusRespectActiveGroupEvenForSuperuser:

    def test_superuser_on_a_permissionless_group_sees_an_empty_menu(self, bootstrap_tenant):
        tenant = bootstrap_tenant("menus-super-guest")
        tenant["user"].is_superuser = True
        tenant["user"].save(update_fields=["is_superuser"])

        guest_group, _ = Group.objects.get_or_create(name=f"Guest-{tenant['entity'].id}")
        # Guest fica sem nenhuma Permission - grupo genuinamente vazio.

        client = _client_for_group(tenant, guest_group)

        response = client.get(f"/api/django_resaas/users/{tenant['user'].id}/menus/")

        assert response.status_code == 200, response.data
        assert response.data == []

    def test_superuser_on_root_still_sees_the_menu(self, bootstrap_tenant):
        """Confirma que a correcção não partiu o caso normal: um
        superuser num grupo com permissões (Root, já com todas as
        permissões CRUD/módulo via create_model_permissions) continua
        a ver o menu. 'hr' é o único módulo activado por omissão pelo
        BootstrapService - 'django_resaas' (saas) só aparece se
        também estiver activo para o EntityType, por isso o teste
        verifica o grupo 'Hr', não 'Engine'."""
        tenant = bootstrap_tenant("menus-super-root")
        tenant["user"].is_superuser = True
        tenant["user"].save(update_fields=["is_superuser"])

        response = tenant["client"].get(
            f"/api/django_resaas/users/{tenant['user'].id}/menus/"
        )

        assert response.status_code == 200, response.data
        hr_menu = next((m for m in response.data if m["menu"] == "Hr"), None)
        assert hr_menu is not None, response.data
        assert len(hr_menu["submenu"]) > 0

    def test_non_superuser_on_guest_also_sees_an_empty_menu(self, bootstrap_tenant):
        """Mesmo comportamento para uma conta normal (não-superuser) -
        garante que a correcção não introduziu nenhuma assimetria
        entre superuser e utilizador normal no mesmo grupo vazio."""
        tenant = bootstrap_tenant("menus-normal-guest")

        guest_group, _ = Group.objects.get_or_create(name=f"Guest2-{tenant['entity'].id}")

        client = _client_for_group(tenant, guest_group)

        response = client.get(f"/api/django_resaas/users/{tenant['user'].id}/menus/")

        assert response.status_code == 200, response.data
        assert response.data == []
