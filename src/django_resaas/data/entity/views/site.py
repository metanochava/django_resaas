from rest_framework.views import APIView

from django_resaas.models.entity_type import EntityType
from django_resaas.models.entity import Entity
from django_resaas.data.entity.serializers.entity import EntitySerializer

from django_resaas.core.utils import all

from urllib.parse import urlparse


class SiteAPIView(APIView):

    def get(self, request):
        origin = request.headers.get("Origin")
        domain = None

        if origin:
            domain = urlparse(origin).netloc

        entity = (
            Entity.objects
            .select_related(
                "theme",
                "typography",
                "layout_settings",
                "animation_settings",
                "entity_type__theme",
                "entity_type__typography",
                "entity_type__layout_settings",
                "entity_type__animation_settings",
            )
            .filter(site=domain)
            .first()
        )


        if not entity:
            return all(request, Origin="Desconhecida")

        tipo = entity.entity_type

        # ------------------------
        # 🔥 FALLBACK SYSTEM
        # ------------------------
        theme = (entity.theme or tipo.theme)
        typography = (entity.typography or tipo.typography)
        layout_settings = (entity.layout_settings or tipo.layout_settings)
        animation_settings = (entity.animation_settings or tipo.animation_settings)

        # ------------------------
        # 🔥 RESPONSE
        # ------------------------
        return all(
            request,
            layout_settings=layout_settings.to_dict() if layout_settings else None,
            theme=theme.to_dict() if theme else None,
            animation_settings=animation_settings.to_dict() if animation_settings else None,
            typography=typography.to_dict() if typography else None,
            entity=EntitySerializer(entity).data
        )