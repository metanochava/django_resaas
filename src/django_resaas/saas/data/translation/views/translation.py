
from django_resaas.saas.core.base.access import ActionPermissionMixin, ExplicitAccessMixin
from rest_framework import filters
from rest_framework import viewsets

from django_resaas.saas.core.utils.pagination import ResaasPagination
from django_resaas.saas.models.translation import Translation
from django_resaas.saas.data.translation.serializers.translation import TranslationSerializer


class TranslationAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED: authenticated callers only (no public actions).
    #
    # Translation rows are GLOBAL (every tenant's UI reads them), so reading
    # needs only authentication, while every write needs the caller's
    # permission in the signed context (ActionPermissionMixin, fail closed).
    membership_actions = ("list", "retrieve")
    action_permissions = {
        "create": "add_translation",
        "update": "change_translation",
        "partial_update": "change_translation",
        "destroy": "delete_translation",
    }

    # Was querying Language/LanguageSerializer - a copy-paste bug that
    # meant GET django_resaas/translations/ actually served Language
    # rows, never a single real Translation (chave/translation) row.
    search_fields = ["chave", "translation"]
    filter_backends = (filters.SearchFilter,)
    serializer_class = TranslationSerializer
    queryset = Translation.objects.all()
    lookup_field = "id"
    pagination_class = ResaasPagination

    def get_queryset(self):
        return self.queryset.select_related("language").order_by(
            "language__name", "chave"
        )