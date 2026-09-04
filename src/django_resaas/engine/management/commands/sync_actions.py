from django.core.management.base import BaseCommand

from django_resaas.engine.core.base.registry import VIEW_REGISTRY
from django_resaas.engine.core.services.action_sync_service import (
    ActionSyncService
)


class Command(BaseCommand):

    help = (
        "Syncs @resaas_action with "
        "ModelExtraAction and Django Permissions. "
        "Legacy alias - see `resaas_sync` for --dry-run/--only support."
    )


    # =========================================================
    # HANDLE
    # =========================================================

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.NOTICE(
                "Syncing RESAAS Actions..."
            )
        )

        # =====================================================
        # VALIDAR REGISTRY
        # =====================================================

        if not VIEW_REGISTRY:

            self.stdout.write(
                self.style.WARNING(
                    "VIEW_REGISTRY is empty. "
                    "No View was found."
                )
            )

            return


        # =====================================================
        # CONTADORES
        # =====================================================

        modules_count = 0
        views_count = 0


        # =====================================================
        # MOSTRAR VIEWS ENCONTRADAS
        # =====================================================

        for module, views in VIEW_REGISTRY.items():

            modules_count += 1

            self.stdout.write(
                f"\nModule: {module}"
            )

            for name, view_class in views.items():

                views_count += 1

                self.stdout.write(
                    f"  - {name}: "
                    f"{view_class.__name__}"
                )


        # =====================================================
        # SINCRONIZAR
        # =====================================================

        try:

            # sync_registry() manages its own transaction (see
            # action_sync_service.py) - resaas_sync hits the exact same
            # call, no service logic is duplicated between the two commands.
            ActionSyncService.sync_registry(
                VIEW_REGISTRY
            )

        except Exception as exc:

            self.stderr.write(
                self.style.ERROR(
                    "\nError syncing "
                    f"RESAAS Actions: {exc}"
                )
            )

            raise


        # =====================================================
        # RESULTADO
        # =====================================================

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "RESAAS Actions synced "
                "successfully."
            )
        )

        self.stdout.write(
            f"Modules found: {modules_count}"
        )

        self.stdout.write(
            f"Views found: {views_count}"
        )