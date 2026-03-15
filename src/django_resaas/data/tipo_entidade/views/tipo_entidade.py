import importlib
import importlib.util

from django.apps import apps
from django.conf import settings as dj_settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils.full_path import FullPath

from django_resaas.models.tipo_entidade import TipoEntidade
from django_resaas.models.entidade import Entidade
from django_resaas.models.entidade_user import EntidadeUser
from django_resaas.models.tipo_entidade_modulo import TipoEntidadeModulo
from django_resaas.models.sucursal_user_group import SucursalUserGroup
from django_resaas.models.tipo_entidade_modelo import TipoEntidadeModelo
from django_resaas.models.entidade_modelo import EntidadeModelo
from django_resaas.models.theme import Theme, Typography
from django_resaas.models.layout_setting import LayoutSetting, AnimationSetting
from django_resaas.data.theme.serializers.theme import ThemeSerializer, TypographySerializer
from django_resaas.data.layout_setting.serializers.layout_setting import LayoutSettingSerializer, AnimationSettingSerializer


from django_resaas.data.tipo_entidade.serializers.tipo_entidade import (
    TipoEntidadeSerializer
)


class TipoEntidadeAPIView(viewsets.ModelViewSet):
    search_fields = ['id', 'nome']
    filter_backends = (filters.SearchFilter,)

    serializer_class = TipoEntidadeSerializer
    queryset = TipoEntidade.objects.all()
    lookup_field = 'id'

    def get_queryset(self):
        if self.request.query_params.get('all'):
            return self.queryset.order_by('ordem')

        self._paginator = None
        return self.queryset.filter(
            estado=1
        ).order_by('ordem')

    @action(detail=True, methods=['GET'])
    def user_entidades(self, request, id):
        entidades = Entidade.objects.filter(
            tipo_entidade__id=id
        )
        resultado = []

        for entidade in entidades:
            try:
                EntidadeUser.objects.get(
                    entidade=entidade,
                    user=request.user
                )
                logo = FullPath.url(request, entidade.logo.name, temporary=False)
                resultado.append(
                    {
                        'id': entidade.id,
                        'nome': entidade.nome,
                        'logo': logo,
                    }
                )
            except EntidadeUser.DoesNotExist:
                continue

        return Response(resultado, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def entidades(self, request, id):
        entidades = Entidade.objects.filter(
            tipo_entidade__id=id
        )
        resultado = [
            {'id': entidade.id, 'nome': entidade.nome}
            for entidade in entidades
        ]
        return Response(resultado, status=status.HTTP_200_OK)

    @action(detail=True, methods=['PUT'])
    def perfilPut(self, request, id):
        group = Group.objects.get(id=request.data['id'])
        group.name = request.data['name']
        group.save()

        return Response(
            {
                'id': group.id,
                'name': group.name,
                'alert_success': Translate.tdc(
                    request,
                    f'Perfil <b>{group.name}</b> actualizado com sucesso'
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['POST'])
    def perfilPost(self, request, id):
        tipo_entidade = TipoEntidade.objects.get(id=id)
        group = Group.objects.create(name=request.data['name'])

        tipo_entidade.groups.add(group)
        for entidade in Entidade.objects.filter(tipo_entidade_id=id):
            entidade.groups.add(group)

        return Response(
            {
                'id': group.id,
                'name': group.name,
                'alert_success': Translate.tdc(
                    request,
                    f'Perfil <b>{group.name}</b> criado com sucesso'
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['GET'])
    def apps(self, request, id):
        resultado = []

        for app in apps.get_app_configs():
            resultado.append(
                {
                    'name': app.name,
                    'label': app.label,
                    'verbose': app.verbose_name,
                }
            )

        for app in dj_settings.INSTALLED_APPS:
            resultado.append(app)

        return Response(resultado, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def modelos(self, request, id):
        tipo_entidade = TipoEntidade.objects.get(id=id)
        modelos = [
            {
                'id': tem.modelo.id,
                'model': tem.modelo.model,
                'app_label': tem.modelo.app_label,
            }
            for tem in TipoEntidadeModelo.filter(tipo_entidade__id=tipo_entidade.id)
        ]
        return Response(modelos, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def addModelo(self, request, id):
        tipo_entidade = TipoEntidade.objects.get(id=id)
        modelo = ContentType.objects.get(id=request.data['id'])

        TipoEntidadeModelo.objects.get_or_create(tipo_entidade__id=tipo_entidade.id, modelo=modelo)
        for entidade in Entidade.objects.filter(tipo_entidade_id=id):
            EntidadeModelo.objects.get_or_create(entidade__id=entidade.id, modelo=modelo)

        return Response(
            {
                'id': modelo.id,
                'model': modelo.model,
                'alert_success': Translate.tdc(
                    request,
                    f'Aplicação <b>{modelo.model}</b> criada com sucesso'
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['POST'])
    def removeModelo(self, request, id):
        tipo_entidade = TipoEntidade.objects.get(id=id)
        modelo = ContentType.objects.get(id=request.data['id'])

        TipoEntidadeModelo.objects.filter(tipo_entidade__id=tipo_entidade.id, modelo=modelo).delete()
        for entidade in Entidade.objects.filter(tipo_entidade_id=id):
            EntidadeModelo.objects.filter(entidade__id=entidade.id, modelo=modelo).delete()

        return Response(
            {
                'id': modelo.id,
                'model': modelo.model,
                'alert_success': Translate.tdc(
                    request,
                    f'Aplicação <b>{modelo.model}</b> removida com sucesso'
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['GET'])
    def modulos(self, request, *args, **kwargs):
        tipo_entidade = self.get_object()
        relacoes = TipoEntidadeModulo.objects.filter(
            tipo_entidade=tipo_entidade.id
        )

        modulos = [
            {
                'id': rel.modelo.id,
                'nome': rel.modelo.nome,
            }
            for rel in relacoes
        ]

        return Response(modulos, status=status.HTTP_200_OK)


    @action(detail=True, methods=['GET'])
    def themeGet(self, request, *args, **kwargs):
        tipoentidade = self.get_object()
        tipoentidade = TipoEntidade.objects.get(id=tipoentidade.id )
        if tipoentidade.theme:
            theme = ThemeSerializer(Theme.objects.get(id=tipoentidade.theme.id)).data
        else:
            theme = {}
        return Response(theme, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def layoutSettingsGet(self, request, *args, **kwargs):
        tipoentidade = self.get_object()
        tipoentidade = TipoEntidade.objects.get(id=tipoentidade.id )
        if tipoentidade.layout_settings:
            layout_settings = LayoutSettingSerializer(LayoutSetting.objects.get(id=tipoentidade.layout_settings.id)).data
        else:
            layout_settings = {}
        return Response(layout_settings, status=status.HTTP_200_OK)

    
    @action(detail=True, methods=['GET'])
    def typographyGet(self, request, *args, **kwargs):
        tipoentidade = self.get_object()
        tipoentidade = TipoEntidade.objects.get(id=tipoentidade.id )
        if tipoentidade.typography:
            typography = TypographySerializer(Typography.objects.get(id=tipoentidade.typography.id)).data
        else:
            typography = {}
        return Response(typography, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def animationSettingsGet(self, request, *args, **kwargs):
        tipoentidade = self.get_object()
        tipoentidade = TipoEntidade.objects.get(id=tipoentidade.id )
        if tipoentidade.animation_settings:
            animation_settings = AnimationSettingSerializer(AnimationSetting.objects.get(id=tipoentidade.animation_settings.id)).data
        else:
            animation_settings = {}
        return Response(animation_settings, status=status.HTTP_200_OK)



    @action(detail=True, methods=['PUT'])
    def themePut(self, request, *args, **kwargs):
        tipoentidade = self.get_object()

        theme = tipoentidade.theme
        data = request.data

        for key, value in data.items():
            if hasattr(theme, key):
                if key == "created_by" or key == "updated_by":
                    theme.created_by = request.user
                    theme.updated_by = request.user
                else:
                    setattr(theme, key, value)

        theme.save()
        theme = ThemeSerializer(theme).data
        return Response(theme, status=status.HTTP_200_OK)


    @action(detail=True, methods=['PUT'])
    def layoutSettingsPut(self, request, *args, **kwargs):
        tipoentidade = self.get_object()

        layout_settings = tipoentidade.layout_settings
        data = request.data

        for key, value in data.items():
            if hasattr(layout_settings, key):
                if key == "created_by" or key == "updated_by":
                    layout_settings.created_by = request.user
                    layout_settings.updated_by = request.user
                else:
                    setattr(layout_settings, key, value)

        layout_settings.save()
        layout_settings = LayoutSettingSerializer(layout_settings).data
        return Response(layout_settings, status=status.HTTP_200_OK)




    @action(detail=True, methods=['PUT'])
    def typographyPut(self, request, *args, **kwargs):
        tipoentidade = self.get_object()

        typography = tipoentidade.typography
        data = request.data

        for key, value in data.items():
            if hasattr(typography, key):
                if key == "created_by" or key == "updated_by":
                    typography.created_by = request.user
                    typography.updated_by = request.user
                else:
                    setattr(typography, key, value)
        typography.save()
        typography = TypographySerializer(typography).data
        return Response(typography, status=status.HTTP_200_OK)


    @action(detail=True, methods=['PUT'])
    def animationSettingsPut(self, request, *args, **kwargs):
        tipoentidade = self.get_object()

        animation_settings = tipoentidade.animation_settings
        data = request.data

        for key, value in data.items():
            if hasattr(animation_settings, key):
                setattr(animation_settings, key, value)
                if key == "created_by" or key == "updated_by":
                    animation_settings.created_by = request.user
                    animation_settings.updated_by = request.user
                else:
                    setattr(animation_settings, key, value)
        

        animation_settings.save()
        animation_settings = AnimationSettingSerializer(animation_settings).data
        return Response(animation_settings, status=status.HTTP_200_OK)


