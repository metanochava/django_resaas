from rest_framework.views import APIView

from django_resaas.models.tipo_entidade import TipoEntidade
from django_resaas.models.entidade import Entidade
from django_resaas.data.entidade.serializers.entidade import EntidadeSerializer

from django_resaas.core.utils import all


class SiteAPIView(APIView):

    def get(self, request):
        origin = request.headers.get("Origin")

        entidade = (
            Entidade.objects
            .select_related(
                "theme",
                "typography",
                "layout_settings",
                "animation_settings",
                "tipo_entidade__theme",
                "tipo_entidade__typography",
                "tipo_entidade__layout_settings",
                "tipo_entidade__animation_settings",
            )
            .filter(site=origin)
            .first()
        )

        if not entidade:
            return all(request, Origin="Desconhecida")

        tipo = entidade.tipo_entidade

        # ------------------------
        # 🔥 FALLBACK SYSTEM
        # ------------------------
        theme = (entidade.theme or tipo.theme)
        typography = (entidade.typography or tipo.typography)
        layout_settings = (entidade.layout_settings or tipo.layout_settings)
        animation_settings = (entidade.animation_settings or tipo.animation_settings)

        # ------------------------
        # 🔥 RESPONSE
        # ------------------------
        return all(
            request,
            layout_settings=layout_settings.to_dict() if layout_settings else None,
            theme=theme.to_dict() if theme else None,
            animation_settings=animation_settings.to_dict() if animation_settings else None,
            typography=typography.to_dict() if typography else None,
            entidade=EntidadeSerializer(entidade).data
        )