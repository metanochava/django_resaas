import importlib
import importlib.util

from django.apps import apps
from django.conf import settings as dj_settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from django_saas.core.utils.translate import Translate
from django_saas.core.utils.full_path import FullPath

from django_saas.models.tipo_entidade import TipoEntidade
from django_saas.models.entidade import Entidade
from django_saas.models.entidade_user import EntidadeUser
from django_saas.models.tipo_entidade_modulo import TipoEntidadeModulo
from django_saas.models.sucursal_user_group import SucursalUserGroup
from django_saas.models.tipo_entidade_modelo import TipoEntidadeModelo
from django_saas.models.entidade_modelo import EntidadeModelo

from django_saas.data.tipo_entidade.serializers.tipo_entidade import (
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
