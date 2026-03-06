import base64
import os
import random

import barcode
import qrcode
from barcode.writer import ImageWriter
from PIL import Image

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.http import Http404

from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django_saas.core.utils.translate import Translate

from django_saas.models.entidade import Entidade
from django_saas.models.entidade_modulo import EntidadeModulo
from django_saas.models.entidade_user import EntidadeUser
from django_saas.models.ficheiro import Ficheiro
from django_saas.models.sucursal import Sucursal
from django_saas.models.sucursal_user import SucursalUser
from django_saas.models.sucursal_user_group import SucursalUserGroup
from django_saas.models.tipo_entidade import TipoEntidade
from django_saas.models.entidade_modelo import EntidadeModelo
from django_saas.models.user import User

from django_saas.data.entidade.serializers.entidade import EntidadeSerializer
from django_saas.data.entidade.serializers.entidade_gravar import EntidadeGravarSerializer
from django_saas.data.entidade.serializers.entidade_user import EntidadeUserSerializer
from django_saas.data.ficheiro.serializers.ficheiro import FicheiroSerializer
from django_saas.data.ficheiro.serializers.ficheiro_gravar import FicheiroGravarSerializer

from django_saas.core.services.disc_manager import DiskManegarService



class EntidadeAPIView(viewsets.ModelViewSet):
    search_fields = ['id', 'nome']
    filter_backends = (filters.SearchFilter,)
    serializer_class = EntidadeSerializer
    queryset = Entidade.objects.all()

    def get_queryset(self, *args, **kwargs):
        return self.queryset.order_by('-id')

    def retrieve(self, request, *args, **kwargs):
        try:
            transformer = self.get_object()
            serializer = EntidadeSerializer(
                transformer,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
        except Http404:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        self._paginator = None
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        transformer = self.get_object()
        entidade = EntidadeSerializer(transformer, data=request.data)

        if entidade.is_valid(raise_exception=True):
            entidade.save()
            return Response(entidade.data, status=status.HTTP_201_CREATED)

        return Response(entidade.errors, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        tipo_entidade_id = request.headers.get('ET')

        if self.request.query_params.get('selfRegist') == 'self':
            request.data['tipo_entidade'] = tipo_entidade_id
            request.data['admin'] = request.user.id

        entidade = EntidadeGravarSerializer(data=request.data)
        entidade.is_valid(raise_exception=True)
        entidade_save = entidade.save()

        EntidadeUser.objects.create(
            user=request.user,
            entidade=entidade_save
        )

        tipo_entidade = TipoEntidade.objects.filter(
            id=entidade_save.tipo_entidade.id
        ).first()

        for group in tipo_entidade.groups.all():
            entidade_save.groups.add(group)

        sucursal = Sucursal.objects.create(
            nome=f"{entidade_save.nome} Sede",
            entidade=entidade_save,
            icon='...',
            label='...'
        )

        SucursalUser.objects.create(
            user=request.user,
            sucursal=sucursal
        )

        user = User.objects.filter(id=request.user.id).first()
        for group in tipo_entidade.groups.all():
            sucursal.groups.add(group)
            user.groups.add(group)

            SucursalUserGroup.objects.create(
                group=group,
                user=request.user,
                sucursal=sucursal
            )

        return Response(entidade.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['GET'])
    def sucursals(self, request, *args, **kwargs):
        transformer = self.get_object()
        sucursals = Sucursal.objects.filter(entidade=transformer)

        return Response(
            [
                {
                    'id': s.id,
                    'nome': s.nome,
                    'estado': s.estado
                }
                for s in sucursals
            ]
        )

    @action(detail=True, methods=['GET'])
    def modelos(self, request, *args, **kwargs):
        entidade = self.get_object()
        return Response(
            [
                {
                    'id': m.modelo.id,
                    'model': m.modelo.model,
                    'app_label': m.modelo.app_label
                }
                for m in EntidadeModelo.objects.filter(entidade__id=entidade.id)
            ],
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['GET'])
    def modulos(self, request, *args, **kwargs):
        entidade = self.get_object()
        ent_mods = EntidadeModulo.objects.filter(entidade=entidade)

        return Response(
            [
                {
                    'id': em.modulo.id,
                    'nome': em.modulo.nome
                }
                for em in ent_mods
            ],
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'])
    def addModelo(self, request, *args, **kwargs):
        entidade = self.get_object()
        modelo = ContentType.objects.get(id=request.data['id'])

        ent, _ = EntidadeModelo.objects.get_or_create(entidade__id=entidade.id, modelo=modelo)

        return Response(
            {
                'id': modelo.id,
                'model': modelo.model,
                'alert_info': f'App <b>{modelo.app_label}</b> criado com sucesso'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['POST'])
    def removeModelo(self, request, *args, **kwargs):
        entidade = self.get_object()
        modelo = ContentType.objects.get(id=request.data['id'])
        EntidadeModelo.objects.filter(entidade__id=entidade.id, modelo=modelo).delete()

        return Response(
            {
                'id': modelo.id,
                'model': modelo.model,
                'alert_info': f'App <b>{modelo.app_label}</b> removido com sucesso'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['GET'])
    def perfils(self, request, *args, **kwargs):
        entidade = self.get_object()
        perfils = sorted(
            [{'id': g.id, 'name': g.name} for g in entidade.groups.all()],
            key=lambda x: x['name']
        )
        return Response(perfils, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def users(self, request, *args, **kwargs):
        transformer = self.get_object()
        search = self.request.query_params.get('search')

        entidade_users = EntidadeUser.objects.filter(
            entidade=transformer,
            user__username__icontains=search,
            deleted_at__isnull=True,
        ).order_by('-user__username')

        page = self.paginate_queryset(entidade_users)
        serializer = EntidadeUserSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['POST'])
    def addUser(self, request, *args, **kwargs):
        transformer = self.get_object()
        user = User.objects.get(id=request.data['user'])

        exists = EntidadeUser.objects.filter(
            entidade=transformer,
            user=user,
            deleted_at__isnull=True
        ).exists()

        if not exists:
            EntidadeUser.objects.create(
                user=user,
                entidade=transformer
            )
            return Response(
                {
                    "alert_seccess": f"O user {user.username} adicionado com sucesso!"
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "alert_seccess": f"O user {user.username} ja existe!"
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['DELETE'])
    def removeUser(self, request, *args, **kwargs):
        transformer = self.get_object()
        entidade_user = EntidadeUser.objects.filter(
            entidade=transformer,
            user__id=request.query_params.get('user'),
            deleted_at__isnull=True
        ).first()

        if entidade_user:
            entidade_user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            "entidade.errors",
            status=status.HTTP_400_BAD_REQUEST
        )



    @action(
        detail=True,
        methods=['POST'],
    )
    def logoPost(self, request, *args, **kwargs):

        transformer = self.get_object()
        entidade = Entidade.objects.get(id=transformer.id)
       
        request.data['entidade'] = str(entidade.id)
        uploaded_file = request.FILES['ficheiro']

        if DiskManegarService.freeSpace(entidade.id, request.FILES['ficheiro']):
            resposta = {'alert_error': 'Nao e possivel fazer upload de ficheiro<br><b>Contacte o adminstrador</b>'}
            return Response(resposta , status=status.HTTP_400_BAD_REQUEST)
        


        try:
            fcr = Ficheiros.objects.get(entidade=entidade, funcionalidade='Logo')
            fcr.delete()
            DiskManegarService.recoverSpace(entidade.id, fcr)
        except:
            print('Nao apgaou')
    

        request.data['size'] = uploaded_file.size
        request.data['modelo'] = 'Entidade'
        request.data['estado'] = 'Activo'
        request.data['funcionalidade'] = 'Logo'

        ficheiro = FicheiroGravarSerializer(data=request.data)
        if ficheiro.is_valid(raise_exception=True):
            ficheiro.save()
            ficheiro = FicheiroSerializer(Ficheiros.objects.get(id=ficheiro.data['id']))
            DiskManegarService.updateSpace(entidade.id, request.FILES['ficheiro'])
            return Response(ficheiro.data, status=status.HTTP_201_CREATED)
        else:
            return Response(ficheiro.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(
        detail=True,
        methods=['GET'],
    )
    def qr(self, request, pk):
        id = pk
        var_qr = {}
        origin = request.headers['Origin']
        LANGUAGE_CODE = 'pt-pt'

        TIME_ZONE = 'UTC'
        settings.LANGUAGE_CODE = 'pt-pt'
        # django.setup()
        print(settings.LANGUAGE_CODE)

        root = settings.MEDIA_ROOT
        lingua = self.request.query_params.get('lang')

        ean = barcode.get('code128', id, writer=ImageWriter())
        filename = ean.save(str(root) +'/' + str(random.random()) + 'qr' + str(random.random()))

        file = Image.open(str(filename))
        file = open(str(filename), 'rb').read()


        blob_barcode = base64.b64encode((file))
        if os.path.exists(filename):
            os.remove(filename)


        qr = qrcode.QRCode(box_size=2)
        qr.add_data(str('var_qr'))
        qr.make()
        img_qr = qr.make_image()
        # img_qr.
        img = img_qr.get_image()

        name = str(root) +'/' + str(random.random()) + 'qr' + str(random.random()) + '.png'
        img_qr.save(name)
        file = Image.open(str(name))
        file = open(str(name), 'rb').read()
        blob = base64.b64encode(bytes(file))
        if os.path.exists(name):
            os.remove(name)


        template_path = 'core/entidade/qr_pdf.html'

        entidade = Entidade.objects.get(id=id)
 
        entidade = EntidadeSerializer(entidade)

        ficheiro  = Ficheiros.objects.get(entidade = id, funcionalidade = 'Logo')

        logo_name = ficheiro.ficheiro.path
        try:
            file = open(logo_name, 'rb').read()
            logo = base64.b64encode(file)
        except:
            logo = ''

        
        url = origin + '/#/?e=' + entidade.data['id'] + '&q=1' 
        var_qr['entidade'] = entidade.data['nome']
        for key, value in var_qr.items():
            url = url + '&' + key + '=' + value
        qr = qrcode.QRCode(box_size=2)
        qr.add_data(str(url))
        qr.make()
        img_qr = qr.make_image()
    

        name = str(root) +'/' + str(random.random()) + 'qr' + str(random.random()) + '.png'
        img_qr.save(name)
        file = Image.open(str(name))
        file = open(str(name), 'rb').read()
        qr_to_scan = base64.b64encode(bytes(file))
        if os.path.exists(name):
            os.remove(name)
        context = {
            'qr': blob,
            'qr_to_scan': qr_to_scan,
            'barcode': blob_barcode, 
            'entidade': entidade.data,
            'logo':logo,
            'titulo': Translate.tdc(lingua, 'QR'),
            'nome': Translate.tdc(lingua, 'Entidade'),
            'de': Translate.tdc(lingua, 'de'),
            'morada': Translate.tdc(lingua, 'Morada'),
            'pagina': Translate.tdc(lingua, 'Pagina')
        }
        
        return Response(context)



    @action(
        detail=True,
        methods=['PUT'],
    )
    def perfilPut(self, request, pk):
        group = Group.objects.get(id=request.data['id'])
        group.name = request.data['name']
        group.save()
        
        perfil = {'id': group.id, 'name': group.name, 'alert_success': 'Perfil <b>'+ group.name + ' </b> actualizado com sucesso'}
        return Response(perfil, status.HTTP_201_CREATED)


    @action(
        detail=True,
        methods=['POST'],
    )
    def perfilPost(self, request, pk):      
        group = Group.objects.create(name=request.data['name'])
        entidade = Entidade.objects.get(id=pk)
        entidade.groups.add(group)

        perfil = {'id': group.id, 'name': group.name, 'alert_success': 'Perfil <b>'+ group.name + ' </b> criado com sucesso'}
        return Response(perfil, status.HTTP_201_CREATED)

