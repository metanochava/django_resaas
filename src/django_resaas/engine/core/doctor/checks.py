"""
Concrete `resaas_doctor` checks. Each one is small, independent, and reads
its own bit of state - no shared setup, no check depending on another
having already run. All of them are read-only: the write+rollback trick
`ActionSyncService.sync_registry(dry_run=True)` uses is the only thing here
that touches the database at all, and it is guaranteed rolled back by
`transaction.set_rollback(True)` before this module ever sees the result -
see its docstring in core/services/action_sync_service.py.
"""

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from django_resaas.engine.core.base.registry import VIEW_REGISTRY
from django_resaas.engine.core.doctor.base import Check, CheckResult, register_check
from django_resaas.engine.core.services.action_sync_service import ActionSyncService
from django_resaas.engine.models.entity_type import EntityType
from django_resaas.engine.models.entity_type_app import EntityTypeApp


@register_check
class DatabaseCheck(Check):
    name = "database"
    label = "Database"

    def run(self):
        try:
            connection.ensure_connection()
        except Exception as exc:
            return [
                CheckResult(
                    "database.unreachable",
                    "error",
                    f"Database unavailable: {exc}",
                    {},
                )
            ]

        return [CheckResult("database.ok", "success", "Database connection OK", {})]


@register_check
class MigrationCheck(Check):
    name = "migrations"
    label = "Migrations"

    def run(self):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        if not plan:
            return [CheckResult("migrations.ok", "success", "No pending migrations", {})]

        pending = [f"{migration.app_label}.{migration.name}" for migration, _backwards in plan]

        return [
            CheckResult(
                "migrations.pending",
                "error",
                f"{len(pending)} pending migration(s)",
                {"migrations": pending},
            )
        ]


@register_check
class RegistryCheck(Check):
    name = "registry"
    label = "Registered Views"

    def run(self):
        if not VIEW_REGISTRY:
            return [
                CheckResult(
                    "registry.empty",
                    "warning",
                    "VIEW_REGISTRY is empty - no view was registered/imported yet",
                    {},
                )
            ]

        results = []
        count = 0
        without_model = 0

        for module_name, views in VIEW_REGISTRY.items():
            for view_name, view_class in views.items():
                count += 1

                if ActionSyncService._get_model_from_view(view_class) is None:
                    without_model += 1
                    # Not a defect: dashboards/reporting endpoints, the
                    # scaffold command view and the notification catalog
                    # are legitimately model-less registered views in this
                    # codebase - they simply aren't eligible for
                    # @resaas_action sync or schema building (ActionCheck/
                    # SchemaCheck already skip them silently for the same
                    # reason). Reported at "info" so a healthy install
                    # doesn't show a permanent WARNING for a normal shape
                    # of view.
                    results.append(
                        CheckResult(
                            "registry.no_model",
                            "info",
                            f"Registered view '{module_name}.{view_name}' "
                            f"({view_class.__name__}) has no resolvable model "
                            "(no queryset / serializer_class.Meta.model) - "
                            "expected for non-CRUD views (dashboards, scaffold, "
                            "catalogs); not eligible for action sync/schema.",
                            {"module": module_name, "view": view_name},
                        )
                    )

        results.append(
            CheckResult(
                "registry.ok",
                "success",
                f"{count} registered view(s), {count - without_model} resolve to a model",
                {"count": count, "without_model": without_model},
            )
        )

        return results


@register_check
class ActionCheck(Check):
    name = "actions"
    label = "Actions"

    def run(self):
        if not VIEW_REGISTRY:
            return [CheckResult("actions.skipped", "info", "Skipped - VIEW_REGISTRY is empty", {})]

        summary = ActionSyncService.sync_registry(VIEW_REGISTRY, dry_run=True)

        results = []
        for identity in summary.created:
            results.append(
                CheckResult(
                    "actions.would_create",
                    "warning",
                    f"Action '{identity}' exists in code but not in persisted metadata "
                    "(run `manage.py resaas_sync`)",
                    {"action": identity},
                )
            )
        for identity in summary.updated:
            results.append(
                CheckResult(
                    "actions.would_update",
                    "warning",
                    f"Action '{identity}' metadata is stale (run `manage.py resaas_sync`)",
                    {"action": identity},
                )
            )
        for identity in summary.deleted:
            results.append(
                CheckResult(
                    "actions.would_delete",
                    "warning",
                    f"Action '{identity}' exists in persisted metadata but no "
                    "corresponding @resaas_action exists in code anymore",
                    {"action": identity},
                )
            )

        if not results:
            results.append(
                CheckResult("actions.ok", "success", "Actions metadata is in sync with code", {})
            )

        return results


@register_check
class SchemaCheck(Check):
    name = "schema"
    label = "Schema Builder"

    def run(self):
        # Imported lazily: app_schema.py pulls in a lot (scaffold service,
        # DRF views, ...) that doctor/checks.py shouldn't force onto every
        # management command's import graph just to offer this one check.
        from django_resaas.engine.core.schema.builder import ResaasSchemaBuilder
        from django_resaas.engine.management.apicommands.view.app_schema import (
            _schema_fields,
        )

        if not VIEW_REGISTRY:
            return [CheckResult("schema.skipped", "info", "Skipped - VIEW_REGISTRY is empty", {})]

        seen_models = set()
        results = []

        for module_views in VIEW_REGISTRY.values():
            for view_class in module_views.values():
                model = ActionSyncService._get_model_from_view(view_class)
                if model is None or model in seen_models:
                    continue
                seen_models.add(model)

                model_label = f"{model._meta.app_label}.{model._meta.model_name}"

                try:
                    fields = _schema_fields(model)
                    ResaasSchemaBuilder(Model=model, fields=fields).build()
                except Exception as exc:
                    results.append(
                        CheckResult(
                            "schema.build_failed",
                            "error",
                            f"Schema build failed for {model_label}: "
                            f"{exc.__class__.__name__}: {exc}",
                            {"model": model_label},
                        )
                    )

        if not results:
            results.append(
                CheckResult(
                    "schema.ok",
                    "success",
                    f"{len(seen_models)} model(s) built a valid Schema 1.0 contract",
                    {"count": len(seen_models)},
                )
            )

        return results


@register_check
class PermissionCheck(Check):
    name = "permissions"
    label = "Permissions"

    # Same convention `create_model_permissions` (core/signals/permissions.py)
    # creates on every post_migrate - kept in sync with that list by hand,
    # same as the signal itself already is.
    CODENAMES = (
        "view", "add", "change", "delete",
        "list", "pdf", "pdf_list", "restore", "hard_delete",
    )

    def run(self):
        if not EntityType.objects.exists():
            return [
                CheckResult(
                    "permissions.skipped",
                    "info",
                    "Skipped - no EntityType exists yet (nothing to check before first bootstrap)",
                    {},
                )
            ]

        my_apps = getattr(settings, "MY_APPS", []) + ["django.contrib.auth"]
        allowed_apps = [app.split(".")[-1] for app in my_apps]

        missing = []

        for model in django_apps.get_models():
            if model._meta.app_label not in allowed_apps:
                continue

            content_type = ContentType.objects.get_for_model(model)

            for codename in self.CODENAMES:
                full_codename = f"{codename}_{model._meta.model_name}"

                if not Permission.objects.filter(
                    codename=full_codename, content_type=content_type
                ).exists():
                    missing.append(f"{model._meta.app_label}.{full_codename}")

        if missing:
            return [
                CheckResult(
                    "permissions.missing",
                    "warning",
                    f"{len(missing)} expected model permission(s) missing "
                    "(created automatically on `manage.py migrate`)",
                    {"missing": missing[:20], "missing_count": len(missing)},
                )
            ]

        return [CheckResult("permissions.ok", "success", "All expected model permissions exist", {})]


@register_check
class ModuleCheck(Check):
    name = "modules"
    label = "Modules"

    def run(self):
        """Structural consistency of module *declarations*
        (App <-> EntityType), never per-tenant *activation* (EntityApp) -
        checking which tenants have which module active is business data,
        out of scope for a structural doctor check, and would mean looping
        over every Entity, which this deliberately never does."""

        broken = []

        for eta in EntityTypeApp.objects.select_related("entity_type", "app"):
            if eta.entity_type_id is None or eta.app_id is None:
                broken.append(eta.id)

        if broken:
            return [
                CheckResult(
                    "modules.broken_link",
                    "error",
                    f"{len(broken)} EntityTypeApp row(s) with a missing entity_type or app",
                    {"ids": broken},
                )
            ]

        return [
            CheckResult(
                "modules.ok",
                "success",
                "EntityType <-> App module declarations are structurally consistent",
                {},
            )
        ]
