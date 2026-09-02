from django_resaas.core.base.views import BaseAPIView, register_view

from django_resaas.notifications.models import NotificationTemplate
from django_resaas.notifications.serializers import NotificationTemplateSerializer


@register_view("templates", module="notifications")
class NotificationTemplateAPIView(BaseAPIView):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
