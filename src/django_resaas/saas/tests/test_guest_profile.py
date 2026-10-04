"""Every user holds the Guest profile in every Branch they belong to (and only
there): core/services/guest_profile_service.py, the BranchUser signal and
`resaas_ensure_guest_profile`."""
from io import StringIO

import pytest
from django.core.management import call_command

from django_resaas.saas.core.services import guest_profile_service as service
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.branch_group import BranchGroup
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db


def _holds_guest(user, branch):
    return BranchUserGroup.objects.filter(user=user, branch=branch, group__name="Guest", state="Active").exists()


def _member(username, branch, *, signal=True):
    user = User.objects.create_user(username=username, email=f"{username}@guest.test", password="Pass-12345")
    if signal:
        BranchUser.objects.create(user=user, branch=branch)
    else:   # a membership that existed before the signal (bulk_create skips post_save)
        BranchUser.objects.bulk_create([BranchUser(user=user, branch=branch)])
    return user


def test_a_new_membership_gets_guest_there(bootstrap_tenant):
    tenant = bootstrap_tenant("guest-new")

    user = _member("guest-ana", tenant["branch"])

    assert _holds_guest(user, tenant["branch"])
    assert BranchGroup.objects.filter(branch=tenant["branch"], group__name="Guest").exists()
    assert EntityGroup.objects.filter(entity=tenant["entity"], group__name="Guest").exists()


def test_never_in_an_entity_the_user_does_not_belong_to(bootstrap_tenant):
    mine = bootstrap_tenant("guest-mine")
    theirs = bootstrap_tenant("guest-theirs")

    user = _member("guest-rui", mine["branch"])

    assert _holds_guest(user, mine["branch"])
    assert not BranchUserGroup.objects.filter(user=user, branch__entity=theirs["entity"]).exists()


def test_every_branch_of_the_user(bootstrap_tenant):
    tenant = bootstrap_tenant("guest-branches")
    second = Branch.objects.create(name="Second", entity=tenant["entity"])

    user = _member("guest-maria", tenant["branch"])
    BranchUser.objects.create(user=user, branch=second)

    assert _holds_guest(user, tenant["branch"]) and _holds_guest(user, second)


def test_ensure_is_idempotent_and_restores_a_removed_guest(bootstrap_tenant):
    tenant = bootstrap_tenant("guest-restore")
    user = _member("guest-ze", tenant["branch"])
    assignment = BranchUserGroup.objects.get(user=user, branch=tenant["branch"], group__name="Guest")
    assignment.delete()   # soft delete

    assert service.ensure_guest(user, tenant["branch"]) is True
    assert _holds_guest(user, tenant["branch"])
    assert service.ensure_guest(user, tenant["branch"]) is False
    assert BranchUserGroup.all_objects.filter(user=user, branch=tenant["branch"], group__name="Guest").count() == 1


def test_the_command_backfills_existing_memberships(bootstrap_tenant):
    tenant = bootstrap_tenant("guest-backfill")
    old = _member("guest-old", tenant["branch"], signal=False)
    assert not _holds_guest(old, tenant["branch"])

    dry = StringIO()
    call_command("resaas_ensure_guest_profile", stdout=dry)
    assert "Dry run" in dry.getvalue() and "guest-old" in dry.getvalue()
    assert not _holds_guest(old, tenant["branch"])

    out = StringIO()
    call_command("resaas_ensure_guest_profile", "--apply", stdout=out)
    assert _holds_guest(old, tenant["branch"])

    again = StringIO()
    call_command("resaas_ensure_guest_profile", stdout=again)
    assert "nothing to do" in again.getvalue()
