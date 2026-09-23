from rest_framework import permissions
from rest_framework.views import APIView

from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.data.entity.serializers.entity import EntitySerializer

from django_resaas.saas.core.utils import all

from django.db.models import Q
from urllib.parse import urlparse


class SiteAPIView(APIView):

    # PUBLIC (explicit): used before there is a session
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        # Entity.site is a URLField, stored WITH its scheme (e.g.
        # "http://clinicaamal.co.mz") - but not consistently: existing rows
        # use http even for sites that are actually served over https, and
        # not every row was entered with the same trailing slash.
        # (Previously this stripped the scheme via urlparse().netloc before
        # filtering, so it compared a bare host against a full URL and could
        # never match anything.) Match on host[:port] only, accepting either
        # scheme and an optional trailing slash, rather than assuming the
        # stored scheme mirrors the request's.
        origin = request.headers.get("Origin")

        entity = None

        if origin:
            netloc = urlparse(origin).netloc

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
                .filter(
                    Q(site=f"http://{netloc}") | Q(site=f"http://{netloc}/") |
                    Q(site=f"https://{netloc}") | Q(site=f"https://{netloc}/")
                )
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