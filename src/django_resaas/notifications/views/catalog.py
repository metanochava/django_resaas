from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_resaas.engine.core.base.views import register_view
from django_resaas.notifications.enums import Category, Channel, Priority
from django_resaas.notifications.models import NotificationRule


@register_view("catalog", module="notifications")
class NotificationCatalogAPIView(APIView):
    """Read-only discovery endpoint for a future Quasar notifications UI
    (spec section 81/80) - additive, outside ResaasSchemaBuilder, so
    Schema 1.0 stays untouched. Lists the channels/categories/priorities
    this engine supports, plus the distinct events this entity already
    has at least one rule configured for."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        entity_id = getattr(request, "entity_id", None)

        events = []
        if entity_id:
            events = list(
                NotificationRule.objects.filter(entity_id=entity_id)
                .order_by("event")
                .values_list("event", flat=True)
                .distinct()
            )

        return Response(
            {
                "channels": Channel.values,
                "categories": Category.values,
                "priorities": Priority.values,
                "events": events,
            }
        )
