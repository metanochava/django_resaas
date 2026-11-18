from rest_framework.response import Response

from django_resaas.saas.core.base.views import BaseAPIView, registerView
from django_resaas.saas.core.decorators.action import resaas_action
from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.core.services import mobile_tab_service
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.data.mobile_tab.serializers.mobile_tab import (
    EntityMobileTabSerializer,
    EntityTypeMobileTabSerializer,
)
from django_resaas.saas.models.mobile_tab import EntityMobileTab, EntityTypeMobileTab


@registerView('entitytypemobiletabs')
class EntityTypeMobileTabAPIView(BaseAPIView):
    """An Entity Type's phone tabs (?entity_type=<id>): Root's (its
    permissions are platform permissions, revoked from Admin)."""
    serializer_class = EntityTypeMobileTabSerializer
    queryset = EntityTypeMobileTab.objects.select_related("entity_type")

    @resaas_action(detail=False, methods=["post"], label="Suggest tabs", icon="auto_awesome",
                   permission="add_entitytypemobiletab")
    def seed(self, request):
        """{entity_type, replace?}: the tabs the Entity Type's active modules
        suggest (<app>/mobile_tabs.py); without replace an Entity Type that
        already has tabs keeps them."""
        entity_type = EntityType.objects.filter(id=request.data.get("entity_type")).first()
        if entity_type is None:
            raise ResaasAPIException("Entity type not found.", code="not_found", status_code=404)
        made = mobile_tab_service.seed_entity_type(entity_type, replace=bool(request.data.get("replace")))
        rows = EntityTypeMobileTab.objects.filter(entity_type=entity_type)
        return Response({"created": made, "results": self.get_serializer(rows, many=True).data})


@registerView('entitymobiletabs')
class EntityMobileTabAPIView(BaseAPIView):
    """The current Entity's own phone tabs (its Admin's): when it has any
    active one, they replace its Entity Type's."""
    serializer_class = EntityMobileTabSerializer
    queryset = EntityMobileTab.objects.all()
