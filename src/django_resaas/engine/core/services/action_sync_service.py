import inspect
from dataclasses import dataclass, field

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from django_resaas.engine.models.model_extra_action import ManagedBy, ModelExtraAction


@dataclass
class SyncOutcome:
    identity: str
    status: str  # "created" | "updated" | "unchanged"


@dataclass
class SyncSummary:
    """Aggregated result of a sync_view()/sync_registry() call. Identities
    are "{app_label}.{model_name}.{action_name}" strings - enough to report
    on (CLI output, doctor checks) without leaking ModelExtraAction rows."""

    created: list = field(default_factory=list)
    updated: list = field(default_factory=list)
    deleted: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)

    def add_outcome(self, outcome):
        getattr(self, outcome.status).append(outcome.identity)

    def add_deleted(self, identity):
        self.deleted.append(identity)

    @property
    def has_changes(self):
        return bool(self.created or self.updated or self.deleted)


class ActionSyncService:

    @classmethod
    def sync_view(cls, view_class, dry_run=False):
        """
        Sincroniza (INSERT/UPDATE) as `@resaas_action` declaradas numa
        única View - cria/actualiza `ModelExtraAction` e `Permission`.

        Deliberadamente NÃO remove órfãos: uma View não sabe, por si só,
        que actions outras Views do MESMO model possam ter declarado
        (ex.: `SaleAPIView.confirm` e `SalePaymentAPIView.payment` no
        model `Sale`) - remover órfãos aqui apagaria essas actions
        legítimas assim que esta View, sozinha, fosse sincronizada.

        Remoção de órfãos é responsabilidade exclusiva de
        `sync_registry()`, que conhece todas as Views registadas antes
        de decidir o que já não existe em código nenhum.

        `dry_run=True` runs the exact same code path (so "what would
        happen" is never a second, divergent implementation to keep in
        sync) inside a transaction that is always rolled back at the end,
        via `transaction.set_rollback(True)` - nothing is persisted,
        guaranteed by Django's own transaction machinery rather than by
        careful avoidance of every write call.
        """

        summary = SyncSummary()

        model = cls._get_model_from_view(view_class)
        if model is None:
            return summary

        app_label = model._meta.app_label
        model_name = model._meta.model_name

        with transaction.atomic():
            content_type = ContentType.objects.get_for_model(model)

            for metadata in cls._get_declared_actions(view_class):
                outcome = cls._sync_action(
                    model=model,
                    content_type=content_type,
                    app_label=app_label,
                    model_name=model_name,
                    metadata=metadata,
                )
                summary.add_outcome(outcome)

            if dry_run:
                transaction.set_rollback(True)

        return summary

    @staticmethod
    def _get_model_from_view(view_class):
        queryset = getattr(view_class, "queryset", None)
        if queryset is not None:
            return queryset.model

        serializer = getattr(view_class, "serializer_class", None)
        meta = getattr(serializer, "Meta", None)

        return getattr(meta, "model", None)

    @staticmethod
    def _get_declared_actions(view_class):
        """
        Discovers every `@resaas_action` declared on `view_class`,
        including ones inherited from mixins/base classes - not just
        the ones defined directly in `view_class.__dict__`.

        Uses `inspect.getmembers`, the same MRO-aware approach DRF's own
        `ViewSetMixin.get_extra_actions()` uses to discover `@action`
        methods: attribute lookup naturally walks the MRO, so if a
        subclass overrides an inherited action (decorated or not), the
        subclass's version is what gets returned here.
        """
        return [
            metadata.copy()
            for _, value in inspect.getmembers(view_class)
            if (metadata := getattr(value, "_resaas_action", None))
        ]

    @classmethod
    def _sync_action(
        cls,
        *,
        model,
        content_type,
        app_label,
        model_name,
        metadata,
    ):
        action_name = metadata["action"]
        # explicit `@resaas_action(permission=...)` wins - lets an
        # action reuse a permission that already exists elsewhere on
        # the same model, instead of always minting `{action}_{model}`
        codename = metadata.get("permission") or f"{action_name}_{model_name}"

        existing_extra = ModelExtraAction.objects.filter(
            app=app_label,
            model=model_name,
            action=action_name,
        ).first()

        # A decorator must never silently take over an action a human
        # deliberately manages by hand - that would rewrite its
        # label/icon/permission/etc. out from under them the next time
        # anything gets synced.
        if existing_extra and existing_extra.managed_by == ManagedBy.MANUAL:
            raise ImproperlyConfigured(
                f"Action '{app_label}.{model_name}.{action_name}' already "
                "exists as a manually managed action. Rename the "
                "decorator action, or explicitly transfer ownership by "
                "setting managed_by='decorator' on the existing "
                "ModelExtraAction row yourself."
            )

        permission, permission_created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={
                "name": f"Can {action_name} {model._meta.verbose_name}"
            },
        )

        permission_managed = (
            existing_extra.permission_managed
            if existing_extra
            else permission_created
        )

        # keep the Permission's display name in sync while the RESAAS
        # mechanism owns it - but never touch a permission a human
        # manages themselves (permission_managed=False), and never
        # rename a permission this action doesn't "own" the naming of
        # (an explicit permission= is, by definition, shared/reused).
        if (
            permission_managed
            and not permission_created
            and not metadata.get("permission")
        ):
            expected_name = f"Can {action_name} {model._meta.verbose_name}"

            if permission.name != expected_name:
                permission.name = expected_name
                permission.save(update_fields=["name"])

        method = ",".join(
            method.upper()
            for method in metadata.get("methods", [])
        )

        defaults = {
            "label": metadata.get("label"),
            "icon": metadata.get("icon"),
            "tooltip": metadata.get("tooltip"),
            "position": metadata.get("position"),
            "order": metadata.get("order", 0),
            "visible": metadata.get("visible", True),
            "autorequest": metadata.get("autorequest", False),
            "method": method,
            "details": metadata.get("detail", False),
            "url": metadata.get("url_path") or action_name,
            "permission": permission.codename,
            "permission_managed": permission_managed,
            "managed_by": ManagedBy.DECORATOR,
        }

        changed = existing_extra is None or any(
            getattr(existing_extra, key) != value
            for key, value in defaults.items()
        )

        ModelExtraAction.objects.update_or_create(
            app=app_label,
            model=model_name,
            action=action_name,
            defaults=defaults,
        )

        status = (
            "created" if existing_extra is None
            else ("updated" if changed else "unchanged")
        )

        return SyncOutcome(
            identity=f"{app_label}.{model_name}.{action_name}",
            status=status,
        )

    @classmethod
    def _remove_orphans(
        cls,
        *,
        content_type,
        app_label,
        model_name,
        current_action_names,
    ):
        queryset = ModelExtraAction.objects.filter(
            app=app_label,
            model=model_name,
            managed_by=ManagedBy.DECORATOR,
        )

        if current_action_names:
            queryset = queryset.exclude(action__in=current_action_names)

        deleted_identities = []

        for extra in queryset:
            # A permission whose codename doesn't match this action's own
            # default convention (f"{action}_{model}") was created via an
            # explicit `permission=` override - by definition meant to be
            # shared/reused, so this one action going orphaned must not
            # assume ownership and delete it too.
            default_codename = f"{extra.action}_{model_name}"
            is_explicit_permission = (
                extra.permission and extra.permission != default_codename
            )

            if (
                extra.permission
                and extra.permission_managed
                and not is_explicit_permission
            ):
                Permission.objects.filter(
                    content_type=content_type,
                    codename=extra.permission,
                ).delete()

            deleted_identities.append(f"{app_label}.{model_name}.{extra.action}")
            extra.delete()

        return deleted_identities

    @classmethod
    def sync_registry(cls, registry, dry_run=False):
        """
        Sincroniza todas as Views registadas.

        Two different views can legitimately declare actions for the
        same model (e.g. `PacienteAPIView.triage` and
        `PacienteExtraAPIView.discharge`). Calling `sync_view()` once
        per view here - each call removing orphans on its own - would
        make the second view's sync see the first view's actions as
        orphaned and delete them.

        Instead, actions are aggregated per (app_label, model_name)
        across every registered view first; orphan removal only runs
        afterwards, once per model, against that combined set.

        `dry_run=True` - see `sync_view()`'s docstring: same code path,
        rolled back via `transaction.set_rollback(True)` at the end, so
        the DB is guaranteed untouched regardless of what ran inside.
        """

        summary = SyncSummary()

        with transaction.atomic():
            content_types_by_key = {}
            action_names_by_key = {}

            for module_views in registry.values():
                for view_class in module_views.values():
                    model = cls._get_model_from_view(view_class)
                    if model is None:
                        continue

                    app_label = model._meta.app_label
                    model_name = model._meta.model_name
                    key = (app_label, model_name)

                    content_types_by_key.setdefault(
                        key, ContentType.objects.get_for_model(model)
                    )
                    current_action_names = action_names_by_key.setdefault(key, set())

                    for metadata in cls._get_declared_actions(view_class):
                        current_action_names.add(metadata["action"])

                        outcome = cls._sync_action(
                            model=model,
                            content_type=content_types_by_key[key],
                            app_label=app_label,
                            model_name=model_name,
                            metadata=metadata,
                        )
                        summary.add_outcome(outcome)

            for key, current_action_names in action_names_by_key.items():
                app_label, model_name = key

                deleted_identities = cls._remove_orphans(
                    content_type=content_types_by_key[key],
                    app_label=app_label,
                    model_name=model_name,
                    current_action_names=current_action_names,
                )
                for identity in deleted_identities:
                    summary.add_deleted(identity)

            if dry_run:
                transaction.set_rollback(True)

        return summary
