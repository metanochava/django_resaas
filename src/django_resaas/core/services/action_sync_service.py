from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from django_resaas.models.model_extra_action import ModelExtraAction


class ActionSyncService:

    @classmethod
    @transaction.atomic
    def sync_view(cls, view_class):
        """Sincroniza as actions RESAAS declaradas numa View."""
        """
        Sincroniza todas as @resaas_action de uma View.

        Faz:
        - INSERT de novas actions
        - UPDATE de actions existentes
        - DELETE de actions removidas do código
        - cria Permission Django quando necessário
        - remove Permission quando a action desaparece,
          desde que a permission tenha sido criada pelo RESAAS
        """

        model = cls._get_model_from_view(view_class)
        if model is None:
            return

        app_label = model._meta.app_label
        model_name = model._meta.model_name
        content_type = ContentType.objects.get_for_model(model)
        declared_actions = cls._get_declared_actions(view_class)
        current_action_names = set()

        for metadata in declared_actions:
            current_action_names.add(metadata["action"])

            cls._sync_action(
                model=model,
                content_type=content_type,
                app_label=app_label,
                model_name=model_name,
                metadata=metadata,
            )

        cls._remove_orphans(
            content_type=content_type,
            app_label=app_label,
            model_name=model_name,
            current_action_names=current_action_names,
        )

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
        return [
            metadata.copy()
            for value in view_class.__dict__.values()
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
        codename = f"{action_name}_{model_name}"

        existing_extra = ModelExtraAction.objects.filter(
            app=app_label,
            model=model_name,
            action=action_name,
        ).first()

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

        method = ",".join(
            method.upper()
            for method in metadata.get("methods", [])
        )

        ModelExtraAction.objects.update_or_create(
            app=app_label,
            model=model_name,
            action=action_name,
            defaults={
                "label": metadata.get("label"),
                "icon": metadata.get("icon"),
                "tooltip": metadata.get("tooltip"),
                "position": metadata.get("position"),
                "order": metadata.get("order", 0),
                "visible": metadata.get("visible", True),
                "method": method,
                "details": metadata.get("detail", False),
                "url": metadata.get("url_path") or action_name,
                "permission": permission.codename,
                "permission_managed": permission_managed,
                "managed_by": "decorator",
            },
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
            managed_by="decorator",
        )

        if current_action_names:
            queryset = queryset.exclude(action__in=current_action_names)

        for extra in queryset:
            if extra.permission and extra.permission_managed:
                Permission.objects.filter(
                    content_type=content_type,
                    codename=extra.permission,
                ).delete()

            extra.delete()

    @classmethod
    @transaction.atomic
    def sync_registry(cls, registry):
        """Sincroniza todas as Views registadas."""

        for module_views in registry.values():
            for view_class in module_views.values():
                cls.sync_view(view_class)