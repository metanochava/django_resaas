"""A new Branch membership (BranchUser) also gets the Guest profile there -
core/services/guest_profile_service.py."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from django_resaas.saas.models.branch_user import BranchUser


@receiver(post_save, sender=BranchUser, dispatch_uid="resaas_guest_profile_on_membership")
def give_guest_profile(sender, instance, created, raw=False, **kwargs):
    if raw or not created:
        return
    from django_resaas.saas.core.services.guest_profile_service import ensure_guest

    ensure_guest(instance.user, instance.branch)
