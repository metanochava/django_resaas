"""manage.py mark_editable_groups - marks as editable only the groups that
belong to one Entity; dry run by default, idempotent."""
from io import StringIO

import pytest
from django.contrib.auth.models import Permission
from django.core.management import call_command

from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_type_group import EntityTypeGroup
from django_resaas.saas.models.group import Group

pytestmark = pytest.mark.django_db


def _group(name, *entities):
    group = Group.objects.create(name=name)
    for tenant in entities:
        EntityGroup.objects.create(entity=tenant["entity"], group=group, state="Active")
    return group


def _run(*args):
    out = StringIO()
    call_command("mark_editable_groups", *args, stdout=out)
    return out.getvalue()


def _editable(group):
    group.refresh_from_db()
    return group.editable


def test_only_exclusive_groups_are_marked(bootstrap_tenant):
    a = bootstrap_tenant("meg-a")
    b = bootstrap_tenant("meg-b")
    own = _group("Own Nurse", a)
    shared = _group("Shared Clerk", a, b)
    template = _group("Template Doctor", a)
    EntityTypeGroup.objects.create(entity_type=a["entity"].entity_type, group=template)
    platform = _group("Platform Ops", a)
    platform.permissions.add(Permission.objects.get(codename="change_entitytype"))
    used_elsewhere = _group("Used Elsewhere", a)
    BranchUserGroup.objects.create(user=b["user"], branch=b["branch"], group=used_elsewhere)
    orphan = Group.objects.create(name="Orphan")

    output = _run("--apply")

    assert _editable(own)
    for group in (shared, template, platform, used_elsewhere, orphan):
        assert not _editable(group), group.name
    assert not _editable(a["root_group"])
    assert "shared by 2 entities" in output
    assert "platform group" in output


def test_dry_run_changes_nothing(bootstrap_tenant):
    a = bootstrap_tenant("meg-dry")
    own = _group("Dry Nurse", a)

    output = _run()

    assert not _editable(own)
    assert "Dry run" in output


def test_running_twice_is_idempotent(bootstrap_tenant):
    a = bootstrap_tenant("meg-twice")
    own = _group("Twice Nurse", a)

    _run("--apply")
    output = _run("--apply")

    assert _editable(own)
    assert "Marked 0 group(s)" in output
