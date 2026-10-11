from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_resaas.saas.core.base.views import register_view
from django_resaas.notifications.enums import Category, Channel, Priority
from django_resaas.notifications.models import NotificationRule
from django_resaas.saas.core.events.lifecycle import lifecycle_event_catalogue
from django_resaas.saas.models.entity_app import EntityApp


@register_view("catalog", module="notifications")
class NotificationCatalogAPIView(APIView):
    """Read-only discovery endpoint for a future Quasar notifications UI
    (spec section 81/80) - additive, outside ResaasSchemaBuilder, so
    Schema 1.0 stays untouched. Lists the channels/categories/priorities
    this saas supports, the distinct events this entity already has at
    least one rule configured for, and the model lifecycle events
    ("<app>.<model>.<action>", core/events/lifecycle.py) of the modules
    active for this entity - what a rule can be attached to without typing
    an event name by hand. Business events emitted by services are not
    listed (there is no registry of them): a rule may still name one."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        entity_id = getattr(request, "entity_id", None)

        events = []
        lifecycle_events = []
        if entity_id:
            active = set(
                EntityApp.objects.filter(entity_id=entity_id, state="Active").values_list("app__name", flat=True)
            )
            lifecycle_events = [name for name in lifecycle_event_catalogue() if name.split(".")[0] in active]

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
                "lifecycle_events": lifecycle_events,
            }
        )
