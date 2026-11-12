"""Form Engine API (saas/core/forms).

    /django_resaas/formdefinitions/            the layers (PROTECTED, per action)
        POST {key, level, entity_type?, branch?, definition}   a new draft version
        POST {id}/publish/                     publish_formdefinition
    /django_resaas/forms/resolve/?key=          the resolved form (members)
    /django_resaas/forms/validate/  {key, data} server-side validation (members)
    /django_resaas/forms/draft/?key=&context=   GET / PUT {data} / DELETE (own)

Layers: platform and entity type need manage_platform_formdefinition (Root);
an Entity / Branch layer is always the caller's own Entity (never the
client's) and its Branch must be one of that Entity's. A published version
never changes or goes away: a change is a new version.
"""
from django.db import IntegrityError, transaction
from django.db.models import Max, Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from django_resaas.saas.core.base.access import ActionPermissionMixin, ExplicitAccessMixin
from django_resaas.saas.core.base.permissions import isPermited
from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.core.forms.resolver import FormNotFound, resolve
from django_resaas.saas.core.forms.validation import validate_submission
from django_resaas.saas.core.tenant.context import ResaasContextService
from django_resaas.saas.data.form_definition.serializers.form_definition import FormDefinitionSerializer
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.form_definition import FormDefinition, FormDraft

PLATFORM_LEVELS = (FormDefinition.LEVEL_PLATFORM, FormDefinition.LEVEL_ENTITY_TYPE)
MANAGE_PLATFORM = "manage_platform_formdefinition"


class _ContextMixin:
    def _check_context(self, request):
        error = getattr(request, "tenant_context_error", None)
        if error:
            raise error if isinstance(error, PermissionDenied) else PermissionDenied(str(error))
        if not getattr(request, "tenant_context", None) or not getattr(request, "entity_id", None):
            raise PermissionDenied("RESAAS context is required.")
        ResaasContextService.validate_for_user(request.user, request.tenant_context)


class FormDefinitionAPIView(_ContextMixin, ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    serializer_class = FormDefinitionSerializer
    action_permissions = {
        "list": "list_formdefinition", "retrieve": "view_formdefinition", "create": "add_formdefinition",
        "update": "change_formdefinition", "partial_update": "change_formdefinition",
        "destroy": "delete_formdefinition", "publish": "publish_formdefinition",
    }

    def initial(self, request, *args, **kwargs):
        self._check_context(request)
        super().initial(request, *args, **kwargs)

    def _platform(self):
        return bool(isPermited(request=self.request, role=MANAGE_PLATFORM))

    def get_queryset(self):
        own = Q(entity_id=self.request.entity_id)
        scope = (own | Q(level__in=PLATFORM_LEVELS)) if self._platform() else own
        queryset = FormDefinition.objects.filter(scope)
        key = self.request.query_params.get("key")
        return queryset.filter(key=key) if key else queryset

    def _scope(self, data):
        """The layer's scope fields from the request, checked."""
        level = data.get("level")
        if level in PLATFORM_LEVELS:
            if not self._platform():
                raise ResaasAPIException("Only the platform keeps platform and entity type forms.",
                                         code="permission_denied", status_code=403)
            if level == FormDefinition.LEVEL_PLATFORM:
                return {"entity_type": None, "entity_id": None, "branch": None}
            if not data.get("entity_type"):
                raise ResaasAPIException("Choose the entity type.", code="invalid_scope",
                                         details={"entity_type": ["Choose the entity type."]})
            return {"entity_id": None, "branch": None}
        scope = {"entity_id": self.request.entity_id, "entity_type": None}
        if level == FormDefinition.LEVEL_BRANCH:
            branch = data.get("branch")
            if not branch or str(branch.entity_id) != str(self.request.entity_id):
                raise ResaasAPIException("Choose a branch of this entity.", code="invalid_scope",
                                         details={"branch": ["Choose a branch of this entity."]})
        else:
            scope["branch"] = None
        return scope

    def perform_create(self, serializer):
        data = serializer.validated_data
        scope = self._scope(data)
        lookup = {"key": data["key"], "level": data["level"],
                  "entity_type": scope.get("entity_type", data.get("entity_type")),
                  "entity_id": scope.get("entity_id"), "branch": scope.get("branch", data.get("branch"))}
        latest = FormDefinition.objects.filter(**lookup).aggregate(v=Max("version"))["v"] or 0
        try:
            with transaction.atomic():
                serializer.save(**scope, version=latest + 1, status=FormDefinition.STATUS_DRAFT,
                                created_by=self.request.user, updated_by=self.request.user, state="Active")
        except IntegrityError:
            raise ResaasAPIException("Another version was saved at the same time; try again.", code="conflict",
                                     status_code=409)

    def _editable(self, instance):
        if instance.status == FormDefinition.STATUS_PUBLISHED:
            raise ResaasAPIException("A published version cannot change: save a new version.",
                                     code="form_published", status_code=409)
        if instance.level in PLATFORM_LEVELS and not self._platform():
            raise ResaasAPIException("Permission denied", code="permission_denied", status_code=403)

    def perform_update(self, serializer):
        self._editable(serializer.instance)
        for name in ("key", "level", "entity_type", "branch"):   # the scope of a version never changes
            serializer.validated_data.pop(name, None)
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        self._editable(instance)
        instance.hard_delete()

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        instance = self.get_object()
        if instance.level in PLATFORM_LEVELS and not self._platform():
            raise ResaasAPIException("Permission denied", code="permission_denied", status_code=403)
        if instance.status != FormDefinition.STATUS_PUBLISHED:
            instance.status = FormDefinition.STATUS_PUBLISHED
            instance.published_at = timezone.now()
            instance.updated_by = request.user
            instance.save(update_fields=["status", "published_at", "updated_by", "updated_at"])
        return Response(self.get_serializer(instance).data)


class FormEngineViewSet(_ContextMixin, ActionPermissionMixin, ExplicitAccessMixin, viewsets.ViewSet):
    """What every member of the Entity needs to fill a form: its resolved
    definition, server-side validation and their own draft (membership: no
    permission, scoped to the caller's Entity / Branch / user)."""

    membership_actions = ("resolve", "validate", "draft")

    def initial(self, request, *args, **kwargs):
        self._check_context(request)
        super().initial(request, *args, **kwargs)

    def _resolved(self, key):
        try:
            return resolve(key, entity_id=self.request.entity_id, branch_id=self.request.branch_id)
        except FormNotFound:
            raise ResaasAPIException("Form not found.", code="form_not_found", status_code=404)

    @action(detail=False, methods=["get"])
    def resolve(self, request):
        return Response(self._resolved(request.query_params.get("key") or ""))

    @action(detail=False, methods=["post"])
    def validate(self, request):
        resolved = self._resolved(request.data.get("key") or "")
        clean, errors = validate_submission(resolved["definition"], request.data.get("data"))
        return Response({"valid": not errors, "errors": errors})

    @action(detail=False, methods=["get", "put", "delete"])
    def draft(self, request):
        key = request.query_params.get("key") or request.data.get("key") or ""
        context = (request.query_params.get("context") or request.data.get("context") or "")[:120]
        if not key:
            raise ResaasAPIException("Name the form.", code="invalid_key", details={"key": ["Name the form."]})
        lookup = {"user": request.user, "entity_id": request.entity_id, "key": key[:120], "context": context}
        if request.method == "GET":
            row = FormDraft.objects.filter(**lookup).first()
            return Response({"data": row.data if row else None, "updated_at": row.updated_at if row else None})
        if request.method == "DELETE":
            FormDraft.objects.filter(**lookup).delete()
            return Response(status=204)
        data = request.data.get("data")
        if not isinstance(data, dict):
            raise ResaasAPIException("The draft is an object.", code="invalid_draft",
                                     details={"data": ["The draft is an object."]})
        row, _ = FormDraft.objects.update_or_create(**lookup, defaults={"data": data, "state": "Active",
                                                                        "updated_by": request.user})
        return Response({"data": row.data, "updated_at": row.updated_at})
