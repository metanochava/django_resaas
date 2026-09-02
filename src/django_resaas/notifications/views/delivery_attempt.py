from rest_framework.response import Response
from rest_framework import status

from django_resaas.core.base.views import BaseAPIView, register_view

from django_resaas.notifications.models import NotificationDeliveryAttempt
from django_resaas.notifications.serializers import (
    NotificationDeliveryAttemptSerializer,
)


@register_view("delivery-attempts", module="notifications")
class NotificationDeliveryAttemptAPIView(BaseAPIView):
    """Read-only audit trail - list/retrieve only."""

    queryset = NotificationDeliveryAttempt.objects.all()
    serializer_class = NotificationDeliveryAttemptSerializer

    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
