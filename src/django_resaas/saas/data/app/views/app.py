from rest_framework import viewsets, status
from django_resaas.saas.core.decorators.action import resaas_action
from rest_framework.response import Response
from rest_framework import filters

from django_resaas.saas.data.app.serializers.app import AppSerializer
from django_resaas.saas.models.app import App
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity_type_app import EntityTypeApp


class AppAPIView(viewsets.ModelViewSet):
    search_fields = ['name']
    filter_backends = (filters.SearchFilter,)
    serializer_class = AppSerializer
    queryset = App.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.order_by('name')

    def list(self, request, *args, **kwargs):
        self._paginator = None
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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

        EntityTypeApp.objects.get_or_create(
            entity_type=entity_type,
            app=app
        )

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