from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from django_resaas.saas.core.base.registry import VIEW_REGISTRY
from django_resaas.saas.core.services.action_sync_service import ActionSyncService
from django_resaas.saas.models.group import Group
from django_resaas.saas.models.model_extra_action import ManagedBy, ModelExtraAction


class Command(BaseCommand):

    help = (
        "Grants every @resaas_action-managed Permission to the 'Root' "
        "group. ActionSyncService creates these Permission rows (via the "
        "post_migrate signal, `sync_actions`, or `resaas_sync`) but never "
        "assigns them to any group - unlike the standard view/add/change/"
        "delete/... permissions bootstrap_service.py grants Root "
        "automatically, granting a custom action's permission is a "
        "deliberate, separate admin step in this framework (see "
        "core/services/action_sync_service.py). Run this after adding or "
        "changing an @resaas_action so 'Root' can actually use it - e.g. "
        "EntityAPIView.addApp/removeApp/addModel/removeModel/apps/models."
    )

    def handle(self, *args, **options):
        # Make sure every @resaas_action currently declared in code has a
        # Permission row before granting - same call the post_migrate
        # signal and `sync_actions`/`resaas_sync` use. VIEW_REGISTRY is
        # only populated once the module declaring the action has been
        # imported (e.g. by urls.py) - if this process never resolved a
        # URL, some actions may still be missing here.
        if VIEW_REGISTRY:
            ActionSyncService.sync_registry(VIEW_REGISTRY)
        else:
            self.stdout.write(self.style.WARNING(
                "VIEW_REGISTRY is empty in this process - nothing was "
                "re-synced. If a @resaas_action you just added is missing "
                "below, run `manage.py resaas_sync` (or restart the app "
                "server, which imports urls.py) first."
            ))

        root_group, _ = Group.objects.get_or_create(name="Root")

        codenames = sorted(set(
            ModelExtraAction.objects
            .filter(managed_by=ManagedBy.DECORATOR)
            .exclude(permission__isnull=True)
            .exclude(permission="")
            .values_list("permission", flat=True)
        ))

        permissions = list(Permission.objects.filter(codename__in=codenames))
        found_codenames = {p.codename for p in permissions}
        missing = [c for c in codenames if c not in found_codenames]

        root_group.permissions.add(*permissions)

        self.stdout.write(self.style.SUCCESS(
            f"Granted {len(permissions)} action permission(s) to 'Root': "
            f"{', '.join(sorted(found_codenames)) or '(none)'}"
        ))

        if missing:
            self.stdout.write(self.style.WARNING(
                "ModelExtraAction references codename(s) with no matching "
                f"Permission row (sync may be out of date): "
                f"{', '.join(missing)}"
            ))
