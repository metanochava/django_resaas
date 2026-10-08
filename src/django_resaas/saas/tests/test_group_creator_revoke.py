"""group_creator(): a profile's `revoke` list is the explicit way to take a
permission away (granting stays additive)."""
import pytest
from django.contrib.auth.models import Permission

from django_resaas.saas.core.utils.group_creator import group_creator
from django_resaas.saas.models.group import Group

pytestmark = pytest.mark.django_db

KEEP, DROP = "view_auditlog", "change_auditlog"


def _codenames(name):
    return set(Group.objects.get(name=name).permissions.values_list("codename", flat=True))


def test_revoke_removes_only_the_listed_permissions_and_is_idempotent():
    assert Permission.objects.filter(codename__in=[KEEP, DROP]).count() == 2
    group_creator([{"name": "Revoke Test", "permissions": [KEEP, DROP]}])
    assert {KEEP, DROP} <= _codenames("Revoke Test")

    profile = {"name": "Revoke Test", "permissions": [KEEP], "revoke": [DROP]}
    first = group_creator([profile])
    second = group_creator([profile])

    assert KEEP in _codenames("Revoke Test")
    assert DROP not in _codenames("Revoke Test")
    assert first["permissions_revoked"]["Revoke Test"] == [DROP]
    assert second["permissions_revoked"]["Revoke Test"] == []


def test_revoke_of_a_permission_the_group_does_not_hold_changes_nothing():
    report = group_creator([{"name": "Revoke None", "permissions": [KEEP], "revoke": [DROP]}])

    assert _codenames("Revoke None") == {KEEP}
    assert report["permissions_revoked"]["Revoke None"] == []


def test_granting_and_revoking_the_same_permission_is_a_configuration_error():
    with pytest.raises(ValueError):
        group_creator([{"name": "Revoke Both", "permissions": [KEEP], "revoke": [KEEP]}])
