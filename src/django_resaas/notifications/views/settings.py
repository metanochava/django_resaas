from django_resaas.core.base.views import BaseAPIView, register_view

from django_resaas.notifications.models import NotificationSettings
from django_resaas.notifications.serializers import NotificationSettingsSerializer


@register_view("settings", module="notifications")
class NotificationSettingsAPIView(BaseAPIView):
    queryset = NotificationSettings.objects.all()
    serializer_class = NotificationSettingsSerializer
