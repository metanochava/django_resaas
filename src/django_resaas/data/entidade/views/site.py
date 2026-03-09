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

from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils import all

class SiteAPIView(APIView):
    def get(self, request):

        domain = request.get_host()
        print(domain)
        try:
            entidade = Entidade.objects.get(site=domain)
        except Exception as e:
            print(e)
        print(domain)
        print(entidade)

        if entidade.theme:
            theme = ThemeSerializer(Theme.objects.get(id=entidade.theme.id)).data
        else:
            tipoentidade = TipoEntidade.objects.get(id=entidade.tipo_entidade.id )
            theme = ThemeSerializer(Theme.objects.get(id=tipoentidade.theme.id)).data
        if entidade.layout_settings:
            ls = LayoutSettingSerializer(LayoutSetting.objects.get(id=entidade.layout_settings.id)).data
        else:
            tipoentidade = TipoEntidade.objects.get(id=entidade.tipo_entidade.id )
            ls = LayoutSettingSerializer(LayoutSetting.objects.get(id=tipoentidade.layout_settings.id)).data
        

       
        return all(request, tayoutSetting = ls, theme = theme,)
