from django_resaas.saas.core.base.access import ActionPermissionMixin, ExplicitAccessMixin
from rest_framework import viewsets, status
from django_resaas.saas.core.decorators.action import resaas_action
from rest_framework.response import Response
from rest_framework import filters

from django_resaas.saas.core.utils.pagination import ResaasPagination
from django_resaas.saas.data.app.serializers.app import AppSerializer
from django_resaas.saas.models.app import App
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity_type_app import EntityTypeApp
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_app import EntityApp


class AppAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED, permission per action (fail closed): the App catalogue is
    # platform administration - only the Root profile holds these codenames
    # (saas/profiles.py revokes them from every other core profile).
    action_permissions = {
        "list": "list_app",
        "retrieve": "view_app",
        "create": "add_app",
        "update": "change_app",
        "partial_update": "change_app",
        "destroy": "delete_app",
        "entityTypes": "view_app",
        "addEntityType": "change_app",
        "removeEntityType": "change_app",
        # apps/{id}/entities/: GET reads (entities), POST links (link_entity)
        "entities": "view_app",
        "link_entity": "change_app",
        "entity": "change_app",
    }

    search_fields = ['name']
    filter_backends = (filters.SearchFilter,)
    serializer_class = AppSerializer
    queryset = App.objects.all()
    lookup_field = "id"
    pagination_class = ResaasPagination

    def get_queryset(self):
        return self.queryset.order_by('name')

    # ===============================
    # 🔥 GET ENTITY TYPES DESTA APP
    # (mesma relação/idioma de EntityTypeAPIView.apps() - só invertido,
    # ver django_resaas.saas.data.entity_type.views.entity_type)
    # ===============================

    @resaas_action(detail=True, methods=['GET'])
    def entityTypes(self, request, id=None):
        app = self.get_object()

        relacoes = EntityTypeApp.objects.filter(
            app=app
        ).select_related('entity_type')

        return Response([
            {
                "id": rel.entity_type.id,
                "name": rel.entity_type.name
            }
            for rel in relacoes
        ], status=status.HTTP_200_OK)

    # ===============================
    # 🔥 ADD ENTITY TYPE
    # ===============================

    @resaas_action(detail=True, methods=['POST'])
    def addEntityType(self, request, id=None):
        app = self.get_object()
        entity_type_id = request.data.get("id")

        entity_type = EntityType.objects.filter(id=entity_type_id).first()
        if not entity_type:
            return Response({"error": "EntityType not found"}, status=400)

        # active, like the other side (EntityTypeAPIView.addApp); adding a
        # link that exists but is inactive activates it
        link, created = EntityTypeApp.objects.get_or_create(
            entity_type=entity_type,
            app=app,
            defaults={"state": "Active"}
        )
        if not created and link.state != "Active":
            link.state = "Active"
            link.save(update_fields=["state"])

        return Response({
            "id": entity_type.id,
            "name": entity_type.name
        }, status=status.HTTP_201_CREATED)

    # ===============================
    # 🔥 REMOVE ENTITY TYPE
    # ===============================
    
    @resaas_action(detail=True, methods=['POST'])
    def removeEntityType(self, request, id=None):
        app = self.get_object()
        entity_type_id = request.data.get("id")

        EntityTypeApp.objects.filter(
            app=app,
            entity_type_id=entity_type_id
        ).delete()

        return Response({"success": True})

    # ===============================
    # ENTITIES THAT USE THIS APP (sub-resource)
    # apps/{id}/entities/            GET  {active: [...], available: [...]}
    #                                POST {entity} -> link (the Entity's type must have the app)
    # apps/{id}/entities/{entity}/   DELETE -> unlink
    # An Entity may only use an app of its EntityType (as EntityAPIView.addApp).
    # ===============================

    @staticmethod
    def _entity_row(entity):
        return {"id": str(entity.id), "name": entity.name,
                "entity_type": entity.entity_type.name if entity.entity_type_id else None}

    @resaas_action(detail=True, methods=["get"], url_path="entities")
    def entities(self, request, id=None):
        """GET: the Entities that use the app, and those whose type allows it."""
        app = self.get_object()
        active_ids = set(EntityApp.objects.filter(app=app, state="Active").values_list("entity_id", flat=True))
        type_ids = EntityTypeApp.objects.filter(app=app, state="Active").values_list("entity_type_id", flat=True)
        entities = Entity.objects.select_related("entity_type").order_by("name")
        return Response({
            "active": [self._entity_row(e) for e in entities.filter(id__in=active_ids)],
            "available": [self._entity_row(e) for e in entities.filter(entity_type_id__in=type_ids).exclude(id__in=active_ids)],
        })

    @entities.mapping.post
    def link_entity(self, request, id=None):
        """POST {entity}: the Entity uses the app (its type must have it); the
        Admin profile gets the app's permissions."""
        from django_resaas.saas.core.services import admin_profile_service
        from django_resaas.saas.core.utils import fail

        app = self.get_object()
        entity = Entity.objects.filter(id=request.data.get("entity")).select_related("entity_type").first() \
            if _is_uuid(request.data.get("entity")) else None
        if entity is None:
            fail(request, "Entity not found.", status=status.HTTP_400_BAD_REQUEST, code="entity_not_found")
        if not EntityTypeApp.objects.filter(entity_type_id=entity.entity_type_id, app=app, state="Active").exists():
            fail(request, "The entity's type does not have this module.", status=status.HTTP_400_BAD_REQUEST,
                 code="app_not_in_entity_type")
        link, created = EntityApp.objects.get_or_create(entity=entity, app=app, defaults={"state": "Active"})
        if not created and link.state != "Active":
            link.state = "Active"
            link.save(update_fields=["state"])
        admin_profile_service.grant_app(app.name)
        return Response(self._entity_row(entity), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @resaas_action(detail=True, methods=["delete"], url_path=r"entities/(?P<entity_id>[^/.]+)")
    def entity(self, request, id=None, entity_id=None):
        app = self.get_object()
        if _is_uuid(entity_id):
            EntityApp.objects.filter(app=app, entity_id=entity_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _is_uuid(value):
    import uuid

    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False
