"""Perfis (Group templates) de administração de plataforma/tenant -
ver saas/profiles.py + saas/apps.py's create_core_profiles(). Mesmo
mecanismo group_creator() já testado indirectamente por
saude/sales/inventory/farmacia's testes de profiles (em
/var/www/dev/back), aqui replicado dentro da própria biblioteca
django_resaas (sem depender de testutils.tenant, que é um helper só do
projecto dev/back)."""
import pytest

from django_resaas.saas.core.utils.group_creator import group_creator
from django_resaas.saas.models.group import Group
from django_resaas.saas.profiles import CORE_PROFILES, CORE_RENAMES

pytestmark = pytest.mark.django_db


def test_core_profiles_are_created_with_permissions():
    group_creator(CORE_PROFILES)

    for name in ("Admin", "Branch Admin"):
        assert Group.objects.filter(name=name).exists(), name
    # removed on 2026-10-11: Admin administers the Entity
    assert not Group.objects.filter(name="System Administrator").exists()
    assert not Group.objects.filter(name="Organization Administrator").exists()


def test_admin_gets_entity_scoped_permissions():
    group_creator(CORE_PROFILES)

    group = Group.objects.get(name="Admin")
    codenames = set(group.permissions.values_list("codename", flat=True))

    assert "add_branch" in codenames
    assert "add_person" in codenames
    # a module (e.g. an application's hr) adds its own permissions to this
    # profile in its own profiles.py - the core names none of them
    assert "add_employee" not in codenames
    # Não cria/apaga EntityType - isso é da plataforma (Root).
    assert "add_entitytype" not in codenames
    assert "change_entitytype" not in codenames


def test_branch_administrator_gets_branch_scoped_permissions_only():
    group_creator(CORE_PROFILES)

    group = Group.objects.get(name="Branch Admin")
    codenames = set(group.permissions.values_list("codename", flat=True))

    assert "add_branchuser" in codenames
    assert "view_person" in codenames
    assert "view_employee" not in codenames
    # Não gere outras Branches nem a própria Entity.
    assert "add_branch" not in codenames
    assert "change_entity" not in codenames


def test_core_profiles_are_idempotent():
    group_creator(CORE_PROFILES)
    group_creator(CORE_PROFILES)

    assert Group.objects.filter(name="Admin").count() == 1


def test_core_profiles_do_not_touch_bootstrap_groups():
    """Guest/Admin/Root (GROUPS, criados por create_django_resaas_groups)
    são grupos de bootstrap/teste sem permissões - group_creator() dos
    perfis nunca lhes dá permissões (ao Admin só retira o catálogo de Apps,
    ver test_app_catalogue_root_only.py)."""
    Group.objects.get_or_create(name="Guest")

    group_creator(CORE_PROFILES)

    guest = Group.objects.get(name="Guest")
    assert guest.permissions.count() == 0


def test_branch_administrator_is_renamed_to_branch_admin_in_place():
    old = Group.objects.create(name="Branch Administrator")

    group_creator(CORE_PROFILES, rename_from=CORE_RENAMES)

    assert not Group.objects.filter(name="Branch Administrator").exists()
    assert Group.objects.get(name="Branch Admin").id == old.id

