"""A Branch membership (BranchUser) also holds the Guest profile there -
core/services/guest_profile_service.py. On creation, and when a removed
membership is restored (a save of a row that is not soft-deleted); the save
that soft-deletes it leaves Guest alone. BranchUser.state is not checked:
memberships are created "Inactive" by default and still count as membership."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from django_resaas.saas.models.branch_user import BranchUser


@receiver(post_save, sender=BranchUser, dispatch_uid="resaas_guest_profile_on_membership")
def give_guest_profile(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    if getattr(instance, "deleted_at", None) is not None:
        return
    from django_resaas.saas.core.services.guest_profile_service import ensure_guest

    ensure_guest(instance.user, instance.branch)
