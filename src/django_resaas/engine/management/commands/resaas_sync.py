from django.core.management.base import BaseCommand

from django_resaas.engine.core.base.registry import VIEW_REGISTRY
from django_resaas.engine.core.services.action_sync_service import ActionSyncService

SYNC_TARGETS = ("actions",)


class Command(BaseCommand):

    help = (
        "Reconciles code-declared RESAAS metadata with persisted metadata "
        "(currently: @resaas_action -> ModelExtraAction/Permission, via the "
        "same ActionSyncService the legacy `sync_actions` command and the "
        "post_migrate signal both use - see core/signals/action_sync.py). "
        "Permissions and Groups are NOT duplicated here: they already "
        "sync automatically on every `manage.py migrate`. This command "
        "never activates a module for a tenant and never picks a tenant "
        "on its own - it only reconciles code-level metadata."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute what would change without writing to the database.",
        )
        parser.add_argument(
            "--only",
            action="append",
            dest="only",
            choices=SYNC_TARGETS,
            help=(
                "Limit sync to specific targets (repeatable). "
                f"Default: all of {SYNC_TARGETS}."
            ),
        )

    def handle(self, *args, **options):
        verbosity = options.get("verbosity", 1)
        dry_run = options["dry_run"]
        targets = options.get("only") or list(SYNC_TARGETS)

        if verbosity >= 1:
            heading = "RESAAS Sync" + (" (dry-run)" if dry_run else "")
            self.stdout.write(self.style.MIGRATE_HEADING(heading))

        if "actions" in targets:
            self._sync_actions(verbosity=verbosity, dry_run=dry_run)

        if verbosity >= 1:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("RESAAS sync complete."))

    def _sync_actions(self, *, verbosity, dry_run):
        if not VIEW_REGISTRY:
            if verbosity >= 1:
                self.stdout.write(
                    self.style.WARNING(
                        "VIEW_REGISTRY is empty - no view was found, nothing to sync."
                    )
                )
            return

        summary = ActionSyncService.sync_registry(VIEW_REGISTRY, dry_run=dry_run)

        create_label = "Would create" if dry_run else "Created"
        update_label = "Would update" if dry_run else "Updated"
        delete_label = "Would delete" if dry_run else "Deleted"

        if verbosity >= 1:
            self.stdout.write("")
            self.stdout.write("Actions:")
            self.stdout.write(f"  {create_label}: {len(summary.created)}")
            self.stdout.write(f"  {update_label}: {len(summary.updated)}")
            self.stdout.write(f"  {delete_label}: {len(summary.deleted)}")
            self.stdout.write(f"  Unchanged:   {len(summary.unchanged)}")

        if verbosity >= 2:
            for label, identities in (
                (create_label, summary.created),
                (update_label, summary.updated),
                (delete_label, summary.deleted),
            ):
                for identity in identities:
                    self.stdout.write(f"    - {label}: {identity}")
