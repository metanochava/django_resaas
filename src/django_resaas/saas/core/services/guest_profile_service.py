"""Every user holds the Guest profile in every Entity / Branch they belong to.

Guest is the core's baseline profile (core/utils/group_creator.py GROUPS):
wherever a user is a member of a Branch (BranchUser), they also hold Guest
there (BranchUserGroup), and Guest is linked to that Branch and its Entity
(BranchGroup / EntityGroup) - only where the user is a member: a user never
gets a profile in an Entity they do not belong to (tenant isolation).

- `ensure_guest(user, branch)` makes it so (idempotent; restores an assignment
  that was soft-deleted or set inactive);
- a post_save signal on BranchUser calls it for every new membership
  (core/signals/guest_profile.py);
- `manage.py resaas_ensure_guest_profile` fixes the users that existed before
  (dry run unless --apply).

Guest is never chosen at login on its own: when a user has one profile besides
Guest, the frontend selects that one (quasar_resaas GroupStore)."""
from django.db import transaction
from django.utils import timezone

GUEST = "Guest"
ACTIVE = "Active"


def guest_group():
    from django_resaas.saas.models.group import Group

    group, _ = Group.objects.get_or_create(name=GUEST)
    return group


def _active(model, **lookup):
    """get_or_create on all rows (soft-deleted included); a deleted or
    inactive row is restored. Returns (row, changed)."""
    manager = getattr(model, "all_objects", model.objects)
    row = manager.filter(**lookup).first()
    if row is None:
        return model.objects.create(**lookup, state=ACTIVE), True
    if row.deleted_at is not None or row.state != ACTIVE:
        row.deleted_at = None
        row.state = ACTIVE
        row.updated_at = timezone.now()
        row.save(update_fields=["deleted_at", "state", "updated_at"])
        return row, True
    return row, False


@transaction.atomic
def ensure_guest(user, branch, group=None):
    """True when something was created or restored."""
    from django_resaas.saas.models.branch_group import BranchGroup
    from django_resaas.saas.models.branch_user_group import BranchUserGroup
    from django_resaas.saas.models.entity_group import EntityGroup

    group = group or guest_group()
    changed = False
    _, c = _active(EntityGroup, entity_id=branch.entity_id, group=group); changed |= c
    _, c = _active(BranchGroup, branch=branch, group=group); changed |= c
    _, c = _active(BranchUserGroup, user=user, branch=branch, group=group); changed |= c
    return changed


def memberships_missing_guest():
    """(user, branch) of every active membership without an active Guest assignment."""
    from django_resaas.saas.models.branch_user import BranchUser
    from django_resaas.saas.models.branch_user_group import BranchUserGroup

    group = guest_group()
    have = set(
        BranchUserGroup.objects.filter(group=group, state=ACTIVE).values_list("user_id", "branch_id")
    )
    return [
        membership for membership in BranchUser.objects.select_related("user", "branch")
        if (membership.user_id, membership.branch_id) not in have
    ]
