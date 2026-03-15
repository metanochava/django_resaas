from django.db import transaction
from django.contrib.auth.models import Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django_resaas.models.tipo_entidade import TipoEntidade
from django_resaas.models.entidade import Entidade
from django_resaas.models.sucursal import Sucursal
from django_resaas.models.entidade_user import EntidadeUser
from django_resaas.models.sucursal_user import SucursalUser
from django_resaas.models.sucursal_user_group import SucursalUserGroup

from django_resaas.models.theme import Theme, Typography
from django_resaas.models.layout_setting import LayoutSetting, AnimationSetting
from django_resaas.data.theme.serializers.theme import ThemeSerializer, TypographySerializer
from django_resaas.data.layout_setting.serializers.layout_setting import LayoutSettingSerializer, AnimationSettingSerializer

from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils import all

class SiteAPIView(APIView):
    def get(self, request):

        origin = request.headers.get("Origin")
        try:
            entidade = Entidade.objects.get(site=origin)
        except Exception as e:
            pass



        if entidade.theme:
            theme = Theme.objects.get(id=entidade.theme.id).to_dict()
        else:
            tipoentidade = TipoEntidade.objects.get(id=entidade.tipo_entidade.id )
            theme = Theme.objects.get(id=tipoentidade.theme.id).to_dict()

        if entidade.typography:
            typography = Typography.objects.get(id=entidade.typography.id).to_dict()
        else:
            tipoentidade = TipoEntidade.objects.get(id=entidade.tipo_entidade.id )
            typography = Typography.objects.get(id=tipoentidade.typography.id).to_dict()

        if entidade.layout_settings:
            layout_settings = LayoutSetting.objects.get(id=entidade.layout_settings.id).to_dict()
        else:
            tipoentidade = TipoEntidade.objects.get(id=entidade.tipo_entidade.id )
            layout_settings = LayoutSetting.objects.get(id=tipoentidade.layout_settings.id).to_dict()
        

        if entidade.animation_settings:
            animation_settings = AnimationSetting.objects.get(id=entidade.animation_settings.id).to_dict()
        else:
            tipoentidade = TipoEntidade.objects.get(id=entidade.tipo_entidade.id )
            animation_settings = AnimationSetting.objects.get(id=tipoentidade.animation_settings.id).to_dict()

        
       
        return all(request, layout_settings = layout_settings, theme = theme, animation_settings= animation_settings, typography= typography, bach_end=request.get_host(), entidade= entidade.id )
