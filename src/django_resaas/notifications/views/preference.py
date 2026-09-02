from django_resaas.core.base.views import BaseAPIView, register_view

from django_resaas.notifications.models import NotificationPreference
from django_resaas.notifications.serializers import NotificationPreferenceSerializer


@register_view("preferences", module="notifications")
class NotificationPreferenceAPIView(BaseAPIView):
    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
