"""Explicit PUBLIC / PROTECTED access for plain (non-BaseAPIView) ViewSets.

DRF's default here is "allow" (REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES is
empty), so a ViewSet that says nothing is PUBLIC. BaseAPIView protects itself in
initial() (permission per action, tenant, module); the older plain
`viewsets.ModelViewSet` views did not - anonymous callers could list user/group
assignments, permissions, groups, ...

`ExplicitAccessMixin` makes them PROTECTED by default (authenticated) and lets a
view list, by name, the few READ actions that are PUBLIC on purpose (the login
screen needs the language list and the branding of an entity type before there
is a session):

    class LanguageAPIView(ExplicitAccessMixin, viewsets.ModelViewSet):
        public_actions = ("list", "retrieve", "translations")

A public action is honoured for safe methods only (GET/HEAD/OPTIONS): a write is
never public. Object/tenant scope and per-action permissions stay where they
were (get_queryset, isPermited, ...): this only decides who may reach the view.
"""
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated

from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin


class ExplicitAccessMixin(ResaasResponseMixin):
    permission_classes = (IsAuthenticated,)

    # READ actions that are PUBLIC on purpose (empty = everything is PROTECTED)
    public_actions = ()

    def get_permissions(self):
        action = getattr(self, "action", None)

        if action in self.public_actions and self.request.method in SAFE_METHODS:
            return [AllowAny()]

        return super().get_permissions()


class ActionPermissionMixin:
    """Per-action authorization for ExplicitAccessMixin views (fail closed).

    ExplicitAccessMixin only decides who may REACH a view (authenticated or
    public). This adds what BaseAPIView does in initial(): every action needs
    its permission in the current signed context, and an action that is not
    declared is denied.

        class EntityAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
            action_permissions = {"update": "change_entity", "addUser": "add_entityuser"}
            membership_actions = ("list", "retrieve")   # scope = get_queryset only

    - `public_actions` (ExplicitAccessMixin) and `membership_actions` are
      the only actions allowed without a permission; membership actions must
      be scoped by the view's get_queryset (the caller's own objects).
    - Missing permission -> 403 permission_denied. Undeclared action -> 403.
    """

    action_permissions = {}
    membership_actions = ()

    def is_membership_request(self, request, action, kwargs):
        """True when this request needs no permission (the view scopes it to
        the caller's own objects). Override for per-object rules."""
        return action in self.membership_actions

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        action = getattr(self, "action", None)

        if action in getattr(self, "public_actions", ()) or self.is_membership_request(request, action, kwargs):
            return

        codename = self.action_permissions.get(action)

        # imported here: base/permissions imports models (app-loading order)
        from django_resaas.saas.core.base.permissions import isPermited
        from django_resaas.saas.core.exceptions import ResaasAPIException

        if not codename or not isPermited(request=request, role=codename):
            raise ResaasAPIException(
                "Permission denied",
                code="permission_denied",
                status_code=403,
            )
