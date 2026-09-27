from rest_framework import permissions
from rest_framework.views import APIView

from django_resaas.saas.models.entity import Entity
from django_resaas.saas.data.entity.serializers.entity import EntitySerializer

from django_resaas.saas.core.utils import all

from django_resaas.saas.core.services.site_service import entity_for_origin


class SiteAPIView(APIView):

    # PUBLIC (explicit): used before there is a session
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        # Entity by the request Origin (host[:port], either scheme, optional
        # trailing slash): site_service.entity_for_origin, shared with the
        # contact form (site/contact/).
        entity = entity_for_origin(
            request.headers.get("Origin"),
            Entity.objects.select_related(
                "theme",
                "typography",
                "layout_settings",
                "animation_settings",
                "entity_type__theme",
                "entity_type__typography",
                "entity_type__layout_settings",
                "entity_type__animation_settings",
            ),
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