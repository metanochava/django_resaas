from django_resaas.saas.core.base.views import BaseAPIView, register_view

from django_resaas.notifications.models import NotificationProviderCredential
from django_resaas.notifications.serializers import NotificationProviderCredentialSerializer


@register_view("provider-credentials", module="notifications")
class NotificationProviderCredentialAPIView(BaseAPIView):
    queryset = NotificationProviderCredential.objects.all()
    serializer_class = NotificationProviderCredentialSerializer
