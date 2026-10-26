from rest_framework import status

from django_resaas.saas.core.base.views import BaseAPIView, register_view
from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.core.services import group_access_service

from django_resaas.notifications.models import NotificationProviderCredential
from django_resaas.notifications.serializers import NotificationProviderCredentialSerializer


@register_view("provider-credentials", module="notifications")
class NotificationProviderCredentialAPIView(BaseAPIView):
    queryset = NotificationProviderCredential.objects.all()
    serializer_class = NotificationProviderCredentialSerializer


@register_view("platform-provider-credentials", module="notifications")
class PlatformNotificationProviderCredentialAPIView(BaseAPIView):
    """The platform default credentials (entity=null): what every tenant
    without its own override uses, ahead of the env vars. Platform level
    only (change_entitytype, Root by default), on top of the usual model
    permission. Rows of an Entity are never listed or changed here."""

    queryset = NotificationProviderCredential.objects.all()
    serializer_class = NotificationProviderCredentialSerializer

    # the rows belong to no Entity/Branch: skip the tenant filter of
    # BaseAPIView.get_queryset and scope to entity=null below instead
    cross_entity_actions = ["list", "retrieve", "update", "partial_update", "destroy"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if not group_access_service.is_platform(request):
            raise ResaasAPIException(
                "Platform level is required.",
                code="permission_denied",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    def get_queryset(self):
        return super().get_queryset().filter(entity__isnull=True, branch__isnull=True)

    def perform_create(self, serializer):
        serializer.save(
            entity=None, branch=None,
            created_by=self.request.user, updated_by=self.request.user,
        )
