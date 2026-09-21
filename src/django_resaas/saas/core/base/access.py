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
