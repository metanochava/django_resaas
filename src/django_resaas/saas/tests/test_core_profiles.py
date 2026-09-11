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
from django_resaas.saas.profiles import CORE_PROFILES

pytestmark = pytest.mark.django_db


def test_core_profiles_are_created_with_permissions():
    group_creator(CORE_PROFILES)

    for name in ("System Administrator", "Organization Administrator", "Branch Administrator"):
        assert Group.objects.filter(name=name).exists(), name


def test_system_administrator_gets_platform_scoped_permissions():
    group_creator(CORE_PROFILES)

    group = Group.objects.get(name="System Administrator")
    codenames = set(group.permissions.values_list("codename", flat=True))

    assert "add_entitytype" in codenames
    assert "add_entity" in codenames
    # Nunca gere Branch directamente - isso é da Entity/Organization
    # Administrator, não da plataforma.
    assert "add_branch" not in codenames


def test_organization_administrator_gets_entity_scoped_permissions():
    group_creator(CORE_PROFILES)

    group = Group.objects.get(name="Organization Administrator")
    codenames = set(group.permissions.values_list("codename", flat=True))

    assert "add_branch" in codenames
    assert "add_employee" in codenames
    assert "add_department" in codenames
    # Não cria/apaga EntityType - isso é da plataforma (System Administrator).
    assert "add_entitytype" not in codenames


def test_branch_administrator_gets_branch_scoped_permissions_only():
    group_creator(CORE_PROFILES)

    group = Group.objects.get(name="Branch Administrator")
    codenames = set(group.permissions.values_list("codename", flat=True))

    assert "add_branchuser" in codenames
    assert "view_employee" in codenames
    # Não gere outras Branches nem a própria Entity.
    assert "add_branch" not in codenames
    assert "change_entity" not in codenames


def test_core_profiles_are_idempotent():
    group_creator(CORE_PROFILES)
    group_creator(CORE_PROFILES)

    assert Group.objects.filter(name="System Administrator").count() == 1


def test_core_profiles_do_not_touch_bootstrap_groups():
    """Guest/Admin/Root (GROUPS, criados por create_django_resaas_groups)
    são grupos de bootstrap/teste sem permissões - group_creator() dos
    perfis nunca deve tocar-lhes."""
    Group.objects.get_or_create(name="Guest")

    group_creator(CORE_PROFILES)

    guest = Group.objects.get(name="Guest")
    assert guest.permissions.count() == 0
