from django_resaas.core.base.views import BaseAPIView, register_view

from django_resaas.notifications.models import NotificationRule
from django_resaas.notifications.serializers import NotificationRuleSerializer


@register_view("rules", module="notifications")
class NotificationRuleAPIView(BaseAPIView):
    queryset = NotificationRule.objects.all()
    serializer_class = NotificationRuleSerializer
