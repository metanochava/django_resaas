from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from rest_framework import filters, status, viewsets
from rest_framework.response import Response

from django_resaas.saas.core.base.access import ActionPermissionMixin, ExplicitAccessMixin
from django_resaas.saas.core.base.permissions import isPermited
from django_resaas.saas.core.decorators.action import resaas_action
from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.data.theme.serializers.theme import ThemeCustomizeSerializer, ThemeSerializer
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.theme import Theme
from django_resaas.saas.models.theme_surface import ThemeSurface

OWNER_FIELDS = ("owner_entity_type", "owner_entity", "owner_user")
COPY_EXCLUDE = {"id", "created_at", "updated_at", "deleted_at", "created_by", "updated_by", "state", *OWNER_FIELDS}


def _denied():
    return ResaasAPIException("Permission denied", code="permission_denied", status_code=403)


class ThemeAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    """Themes: templates (no owner) and customized copies owned by one
    EntityType, Entity or User.

    PROTECTED (authenticated). Who sees what (get_queryset): the templates,
    the themes of the caller, of the Entity of the signed context and of that
    Entity's EntityType - never another user's or another organisation's.
    Who changes what (per object, _can_write):

        template            change_theme / delete_theme (Root)
        owner entity_type   change_entitytype
        owner entity        change_entity, in that Entity's signed context
        owner user          that user

    `customize` copies a visible theme for one level and applies it there."""

    filter_backends = (filters.SearchFilter,)
    serializer_class = ThemeSerializer
    queryset = Theme.objects.all()

    action_permissions = {"create": "add_theme"}
    # scoped by get_queryset; writes are checked per object below
    membership_actions = ("list", "retrieve", "update", "partial_update", "destroy", "customize")

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return self.queryset.all()

        visible = Q(owner_entity_type__isnull=True, owner_entity__isnull=True, owner_user__isnull=True)
        visible |= Q(owner_user=user)
        entity_id = getattr(self.request, "entity_id", None)
        if entity_id:
            visible |= Q(owner_entity_id=entity_id)
            entity_type_id = Entity.objects.filter(pk=entity_id).values_list("entity_type_id", flat=True).first()
            if entity_type_id:
                visible |= Q(owner_entity_type_id=entity_type_id)
        return self.queryset.filter(visible)

    # ------------------------------------------------------------ authorization

    def _can_write(self, theme, deleting=False):
        request = self.request
        if getattr(request.user, "is_superuser", False):
            return True
        if theme.owner_user_id:
            return theme.owner_user_id == request.user.id
        if theme.owner_entity_id:
            return (
                str(theme.owner_entity_id) == str(getattr(request, "entity_id", None))
                and isPermited(request=request, role="change_entity")
            )
        if theme.owner_entity_type_id:
            return isPermited(request=request, role="change_entitytype")
        return isPermited(request=request, role="delete_theme" if deleting else "change_theme")

    def perform_update(self, serializer):
        if not self._can_write(serializer.instance):
            raise _denied()
        serializer.save()

    def perform_destroy(self, instance):
        if not self._can_write(instance, deleting=True):
            raise _denied()
        instance.delete()

    # ------------------------------------------------------------ customize

    def _target(self, scope, target_id):
        """(object that gets the theme, owner kwargs) or a 403."""
        request = self.request
        superuser = getattr(request.user, "is_superuser", False)

        if scope == "user":
            if target_id and str(target_id) != str(request.user.id) and not superuser:
                raise _denied()
            from django_resaas.saas.models.user import User

            user = User.objects.filter(pk=target_id).first() if target_id else request.user
            if user is None:
                raise ResaasAPIException("User not found.", code="not_found", status_code=404)
            return user, {"owner_user": user}

        if scope == "entity":
            entity_id = target_id or getattr(request, "entity_id", None)
            if not entity_id:
                raise ResaasAPIException("No Entity selected.", code="entity_required", status_code=400)
            if not superuser and (
                str(entity_id) != str(getattr(request, "entity_id", None))
                or not isPermited(request=request, role="change_entity")
            ):
                raise _denied()
            entity = Entity.objects.filter(pk=entity_id).first()
            if entity is None:
                raise ResaasAPIException("Entity not found.", code="not_found", status_code=404)
            return entity, {"owner_entity": entity}

        if not target_id:
            raise ResaasAPIException("The entity type is required.", code="entity_type_required", status_code=400)
        if not superuser and not isPermited(request=request, role="change_entitytype"):
            raise _denied()
        entity_type = EntityType.objects.filter(pk=target_id).first()
        if entity_type is None:
            raise ResaasAPIException("Entity type not found.", code="not_found", status_code=404)
        return entity_type, {"owner_entity_type": entity_type}

    @resaas_action(detail=True, methods=["POST"])
    def customize(self, request, pk=None):
        """POST themes/{id}/customize/ {scope, target?, name?, values?} - 201
        with the new theme, already applied to the target's `theme`."""
        source = self.get_object()  # only a theme the caller can see
        payload = ThemeCustomizeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        target, owner = self._target(data["scope"], data.get("target"))
        level_name = getattr(target, "name", None) or getattr(target, "username", "") or ""

        fields = [field.name for field in Theme._meta.concrete_fields if field.name not in COPY_EXCLUDE]
        copied = model_to_dict(source, fields=fields)
        copied.update(data.get("values") or {})
        copied["name"] = (data.get("name") or "").strip() or f"{source.name} ({level_name})"[:100]

        with transaction.atomic():
            theme = Theme.objects.create(**copied, **owner)
            surface_fields = [
                field.name for field in ThemeSurface._meta.concrete_fields
                if field.name not in {"id", "theme", "created_at", "updated_at", "deleted_at", "created_by", "updated_by"}
            ]
            for surface in ThemeSurface.objects.filter(theme=source):
                ThemeSurface.objects.create(theme=theme, **model_to_dict(surface, fields=surface_fields))
            target.theme = theme
            target.save(update_fields=["theme"])

        return Response(ThemeSerializer(theme, context={"request": request}).data, status=status.HTTP_201_CREATED)
