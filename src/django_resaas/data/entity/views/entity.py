import base64
import os
import random

from django_resaas.core.utils import make_qr_b64, make_barcode_b64, png_bytes_to_b64, PDF

import barcode
import qrcode
from barcode.writer import ImageWriter
from PIL import Image
from django.db import transaction


from django.conf import settings
from django_resaas.models.group import Group
from django.contrib.contenttypes.models import ContentType
from django.http import Http404

from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django_resaas.core.utils.translate import Translate

from django_resaas.models.entity import Entity
from django_resaas.models.entity_app import EntityApp
from django_resaas.models.entity_user import EntityUser
from django_resaas.models.file import File
from django_resaas.models.branch import Branch
from django_resaas.models.branch_user import BranchUser
from django_resaas.models.branch_group import BranchGroup
from django_resaas.models.branch_user_group import BranchUserGroup
from django_resaas.models.entity_type import EntityType
from django_resaas.models.entity_type_group import EntityTypeGroup
from django_resaas.models.entity_type_app import EntityTypeApp
from django_resaas.models.entity_model import EntityModel
from django_resaas.models.entity_group import EntityGroup
from django_resaas.models.user import User

from django_resaas.data.entity.serializers.entity import EntitySerializer
from django_resaas.data.entity.serializers.entity_gravar import EntityGravarSerializer
from django_resaas.data.entity.serializers.entity_user import EntityUserSerializer
from django_resaas.data.file.serializers.file import FileSerializer
from django_resaas.data.file.serializers.file_gravar import FileGravarSerializer

from django_resaas.models.theme import Theme, Typography
from django_resaas.models.layout_setting import LayoutSetting, AnimationSetting
from django_resaas.data.theme.serializers.theme import ThemeSerializer, TypographySerializer
from django_resaas.data.layout_setting.serializers.layout_setting import LayoutSettingSerializer, AnimationSettingSerializer
from django_resaas.core.utils import ok


from django_resaas.core.services.disc_manager import DiskManegarService



class EntityAPIView(viewsets.ModelViewSet):
    search_fields = ['id', 'name']
    filter_backends = (filters.SearchFilter,)
    serializer_class = EntitySerializer
    queryset = Entity.objects.all()

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        queryset = super().get_queryset()

        # 👑 superuser → vê tudo
        if user.is_superuser:
            return queryset

        # 👤 user normal → filtra por entidade
        entity_id = getattr(self.request, "entity_id", None)

        if not entity_id:
            return queryset.none()

        return queryset.filter(
            entityuser__entity_id=entity_id
        ).distinct()

    def retrieve(self, request, *args, **kwargs):
        try:
            transformer = self.get_object()
            serializer = EntitySerializer(
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
        partial = request.method == 'PATCH'

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        
        # ------------------------
        # 🔥 SELF REGISTER
        # ------------------------
        if request.query_params.get('selfRegist') == 'self':
            data['entity_type'] = request.entity_type_id
            data['admins'][0] = request.user.id


        # ------------------------
        # 🔥 VALIDAR E CRIAR ENTIDADE
        # ------------------------
        serializer = EntityGravarSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        entity = serializer.save()

        # ------------------------
        # 🔥 TIPO ENTIDADE
        # ------------------------
        entity_type = EntityType.objects.get(
            id=entity.entity_type.id
        )

        for te in EntityTypeApp.objects.filter(entity_type=entity_type):
            entity_app, _ = EntityApp.objects.get_or_create(
                app=te.app,
                entity=entity,
                estado = 1
            )

        for u in data['admins']:
            user = User.objects.get(id = u)
           
            # ------------------------
            # 🔥 RELAÇÃO USER ↔ ENTIDADE
            # ------------------------
            entity.admins.add(user)

            EntityUser.objects.get_or_create(
                user=user,
                entity=entity,
                estado = 1
            )
         
            # ------------------------
            # 🔥 HERDAR GRUPOS DO TIPO ENTIDADE
            # ------------------------
            for te in EntityTypeGroup.objects.filter(entity_type = entity.entity_type.id ):

                EntityGroup.objects.get_or_create(
                    entity = entity,
                    group = te.group,
                    estado = 1
                )
                user.groups.add(te.group)

            # ------------------------
            # 🔥 SUCURSAL PRINCIPAL
            # ------------------------
            branch = Branch.objects.create(
                name=f"{entity.name} Main",
                entity=entity,
                estado = 1,
                icon='...',
                label='...'
            )

            # ------------------------
            # 🔥 RELAÇÃO USER ↔ SUCURSAL
            # ------------------------
            BranchUser.objects.get_or_create(
                user=user,
                branch=branch,
                estado = 1
            )

            # ------------------------
            # 🔥 GRUPOS NA SUCURSAL
            # ------------------------
            for e in EntityGroup.objects.filter(entity = entity.id ):

                BranchGroup.objects.get_or_create(
                    branch=branch,
                    group=e.group,
                    estado = 1
                )

                BranchUserGroup.objects.get_or_create(
                    user=user,
                    branch=branch,
                    group=e.group,
                    estado = 1
                )
            

        # ------------------------
        # 🔥 RESPONSE
        # ------------------------
        return ok(
            request,
            "Entity criada com sucesso",
            entity_type=entity_type.name,
            entity=entity.name,
            branch=branch.name,
            usuario=user.username,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['GET'])
    def branchs(self, request, *args, **kwargs):
        transformer = self.get_object()
        branchs = Branch.objects.filter(entity=transformer)

        return Response(
            [
                {
                    'id': s.id,
                    'name': s.name,
                    'estado': s.estado
                }
                for s in branchs
            ]
        )

    @action(detail=True, methods=['GET'])
    def models(self, request, *args, **kwargs):
        entity = self.get_object()
        return Response(
            [
                {
                    'id': m.model.id,
                    'model': m.model.model,
                    'app_label': m.model.app_label
                }
                for m in EntityModel.objects.filter(entity__id=entity.id)
            ],
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['GET'])
    def apps(self, request, *args, **kwargs):
        entity = self.get_object()
        ent_mods = EntityApp.objects.filter(entity=entity)

        return Response(
            [
                {
                    'id': em.app.id,
                    'name': em.app.name
                }
                for em in ent_mods
            ],
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'])
    def addModel(self, request, *args, **kwargs):
        entity = self.get_object()
        model = ContentType.objects.get(id=request.data['id'])

        ent, _ = EntityModel.objects.get_or_create(entity__id=entity.id, model=model)

        return Response(
            {
                'id': model.id,
                'model': model.model,
                'alert_info': f'App <b>{model.app_label}</b> criado com sucesso'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['POST'])
    def removeModel(self, request, *args, **kwargs):
        entity = self.get_object()
        model = ContentType.objects.get(id=request.data['id'])
        EntityModel.objects.filter(entity__id=entity.id, model=model).delete()

        return Response(
            {
                'id': model.id,
                'model': model.model,
                'alert_info': f'App <b>{model.app_label}</b> removido com sucesso'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['GET'])
    def profiles(self, request, *args, **kwargs):
        entity = self.get_object()
        profiles = sorted(
            [{'id': g.id, 'name': g.name} for g in entity.groups.all()],
            key=lambda x: x['name']
        )
        return Response(profiles, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def users(self, request, *args, **kwargs):
        transformer = self.get_object()
        search = self.request.query_params.get('search')

        entity_users = EntityUser.objects.filter(
            entity=transformer,
            user__username__icontains=search,
            deleted_at__isnull=True,
        ).order_by('-user__username')

        page = self.paginate_queryset(entity_users)
        serializer = EntityUserSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['POST'])
    def addUser(self, request, *args, **kwargs):
        transformer = self.get_object()
        user = User.objects.get(id=request.data['user'])

        exists = EntityUser.objects.filter(
            entity=transformer,
            user=user,
            deleted_at__isnull=True
        ).exists()

        if not exists:
            EntityUser.objects.create(
                user=user,
                entity=transformer,
                estado = 1
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
        entity_user = EntityUser.objects.filter(
            entity=transformer,
            user__id=request.query_params.get('user'),
            deleted_at__isnull=True
        ).first()

        if entity_user:
            entity_user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            "entity.errors",
            status=status.HTTP_400_BAD_REQUEST
        )


    @action(
        detail=True,
        methods=['POST'],
    )
    def logoPost(self, request, *args, **kwargs):

        transformer = self.get_object()
        entity = Entity.objects.get(id=transformer.id)
       
        request.data['entity'] = str(entity.id)
        uploaded_file = request.FILES['file']

        if DiskManegarService.freeSpace(entity.id, request.FILES['file']):
            resposta = {'alert_error': 'Nao e possivel fazer upload de file<br><b>Contacte o adminstrador</b>'}
            return Response(resposta , status=status.HTTP_400_BAD_REQUEST)
        


        try:
            fcr = Files.objects.get(entity=entity, funcionalidade='Logo')
            fcr.delete()
            DiskManegarService.recoverSpace(entity.id, fcr)
        except:
            pass

    

        request.data['size'] = uploaded_file.size
        request.data['model'] = 'Entity'
        request.data['estado'] = 1
        request.data['funcionalidade'] = 'Logo'

        file = FileGravarSerializer(data=request.data)
        if file.is_valid(raise_exception=True):
            file.save()
            file = FileSerializer(Files.objects.get(id=file.data['id']))
            DiskManegarService.updateSpace(entity.id, request.FILES['file'])
            return Response(file.data, status=status.HTTP_201_CREATED)
        else:
            return Response(file.errors, status=status.HTTP_400_BAD_REQUEST)


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


        template_path = 'core/entity/qr_pdf.html'

        entity = Entity.objects.get(id=id)
 
        entity = EntitySerializer(entity)

        file  = Files.objects.get(entity = id, funcionalidade = 'Logo')

        logo_name = file.file.path
        try:
            file = open(logo_name, 'rb').read()
            logo = base64.b64encode(file)
        except:
            logo = ''

        
        url = origin + '/#/?e=' + entity.data['id'] + '&q=1' 
        var_qr['entity'] = entity.data['name']
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
            'entity': entity.data,
            'logo':logo,
            'titulo': Translate.tdc(lingua, 'QR'),
            'name': Translate.tdc(lingua, 'Entity'),
            'de': Translate.tdc(lingua, 'de'),
            'morada': Translate.tdc(lingua, 'Morada'),
            'pagina': Translate.tdc(lingua, 'Pagina')
        }
        
        return Response(context)



    @action(detail=True, methods=['GET'])
    def themeGet(self, request, *args, **kwargs):
        entity = self.get_object()
        entity = Entity.objects.get(id=entity.id )

        if entity.theme:
            theme = ThemeSerializer(Theme.objects.get(id=entity.theme.id)).data
        else:
            entitytype = EntityType.objects.get(id=entity.entity_type.id )
            theme = ThemeSerializer(Theme.objects.get(id=entitytype.theme.id)).data
        return Response(theme, status=status.HTTP_200_OK)


    @action(detail=True, methods=['PUT'])
    def themePut(self, request, *args, **kwargs):
        entity = self.get_object()
        theme = entity.theme or Theme.objects.create()
        if not entity.theme:
            entity.theme = theme
            entity.save()

        theme = Theme.objects.get(id=entity.theme.id)
        data = request.data

        for key, value in data.items():
            if key == "created_by" or key == "updated_by":
                theme.created_by = request.user
                theme.updated_by = request.user
            else:
                setattr(theme, key, value)
        theme.save()
        theme = ThemeSerializer(theme).data
        return ok(request, 'Cores actualizadas com sucesso!',theme=theme)

    @action(detail=True, methods=['GET'])
    def layoutSettingsGet(self, request, *args, **kwargs):
        entity = self.get_object()
        entity = Entity.objects.get(id=entity.id)
        if entity.layout_settings:
            ls = LayoutSettingSerializer(LayoutSetting.objects.get(id=entity.layout_settings.id)).data
        else:
            entitytype = EntityType.objects.get(id=entity.entity_type.id )
            ls = LayoutSettingSerializer(LayoutSetting.objects.get(id=entitytype.layout_settings.id)).data
        return Response(ls, status=status.HTTP_200_OK)


    @action(detail=True, methods=['PUT'])
    def layoutSettingsPut(self, request, *args, **kwargs):
        entity = self.get_object()
        layout_settings = entity.layout_settings or LayoutSetting.objects.create()
        if not entity.layout_settings:
            entity.layout_settings = layout_settings
            entity.save()


        layout_settings = LayoutSetting.objects.get(id=entity.layout_settings.id)
        data = request.data

        for key, value in data.items():
            if key == "created_by" or key == "updated_by":
                layout_settings.created_by = request.user
                layout_settings.updated_by = request.user
            else:
                setattr(layout_settings, key, value)

        layout_settings.save()
        layout_settings = LayoutSettingSerializer(layout_settings).data
        return ok(request, 'Layout actualizado com sucesso!',layout_settings=layout_settings)







    @action(detail=True, methods=['GET'])
    def typographyGet(self, request, *args, **kwargs):
        entity = self.get_object()
        entity = Entity.objects.get(id=entity.id )

        if entity.typography:
            typography = TypographySerializer(Typography.objects.get(id=entity.typography.id)).data
        else:
            entitytype = EntityType.objects.get(id=entity.entity_type.id )
            typography = TypographySerializer(Typography.objects.get(id=entitytype.typography.id)).data
        return Response(typography, status=status.HTTP_200_OK)

    @action(detail=True, methods=['PUT'])
    def typographyPut(self, request, *args, **kwargs):
        entity = self.get_object()
        typography = entity.typography or Typography.objects.create()
        if not entity.typography:
            entity.typography = typography
            entity.save()

        typography = Typography.objects.get(id=entity.typography.id)
        data = request.data

        for key, value in data.items():
            if key == "created_by" or key == "updated_by":
                typography.created_by = request.user
                typography.updated_by = request.user
            else:
                setattr(typography, key, value)
        typography.save()
        typography = TypographySerializer(typography).data
        return ok(request, 'Fonte actualizada com sucesso!',typography=typography)




    @action(detail=True, methods=['GET'])
    def animationSettingsGet(self, request, *args, **kwargs):
        entity = self.get_object()
        entity = Entity.objects.get(id=entity.id)
        if entity.animation_settings:
            animation_settings = AnimationSettingSerializer(AnimationSetting.objects.get(id=entity.animation_settings.id)).data
        else:
            entitytype = EntityType.objects.get(id=entity.entity_type.id )
            animation_settings = AnimationSettingSerializer(AnimationSetting.objects.get(id=entitytype.animation_settings.id)).data
        return Response(animation_settings, status=status.HTTP_200_OK)


    @action(detail=True, methods=['PUT'])
    def animationSettingsPut(self, request, *args, **kwargs):
        entity = self.get_object()
        animation_settings = entity.animation_settings or AnimationSetting.objects.create()
        if not entity.animation_settings:
            entity.animation_settings = animation_settings
            entity.save()


        animation_settings = AnimationSetting.objects.get(id=entity.animation_settings.id)
        data = request.data

        for key, value in data.items():
            if key == "created_by" or key == "updated_by":
                animation_settings.created_by = request.user
                animation_settings.updated_by = request.user
            else:
                setattr(animation_settings, key, value)

        animation_settings.save()
        animation_settings = AnimationSettingSerializer(animation_settings).data
        return ok(request, 'Animacao actualizado com sucesso!',animation_settings=animation_settings)



    @action(
        detail=True,
        methods=['GET'],
    )
    def pdf(self, request, *args, **kwargs):
        entity = self.get_object()

        # Normalmente você busca no DB
        # invoice = Invoice.objects.get(id=invoice_id)
        # Exemplo de dados (substituir por dados reais)
        company = {
            "name": "Minha Empresa Lda",
            "address": "Rua X, Luanda, Angola",
            "nif": "5000000000",
            "phone": "+244 900 000 000",
            "email": "finance@empresa.co.ao",
        }

        customer = {
            "name": "Cliente Exemplo",
            "nif": "4000000000",
            "address": "Rua Y, Benguela, Angola",
            "email": "cliente@email.com",
            "phone": "+244 999 999 999",
        }

        doc = {
            "type": "FATURA",
            "number": "FT 2026/000123",
            "date": "2026-02-05",
            "due_date": "2026-02-10",
            "currency": "AOA",
            "payment_method": "Transferência",
            "reference": "REF-001",
            "notes": "Obrigado pela preferência.",
        }

        lines = [
            {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
            {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        ]

        totals = {
            "subtotal": "60.000,00",
            "vat_total": "8.400,00",
            "discount_total": "0,00",
            "grand_total": "68.400,00",
        }

        logo_b64 = None
        with open(entity.logo.path, "rb") as f:
            logo_b64 = png_bytes_to_b64(f.read())



        qr_b64 = make_qr_b64(f"{doc['type']}|{doc['number']}|TOTAL:{totals['grand_total']}")
        barcode_b64 = make_barcode_b64(doc["number"])
        

        return PDF("django_resaas/invoice.html", request,  company= company, customer= customer, doc= doc, lines= lines, totals= totals, logo_b64= logo_b64, qr_b64= qr_b64, barcode_b64= barcode_b64,)

    
    # ===============================
    # 🔥 GROUPS (FINAL LIMPO)
    # ===============================

    @action(detail=True, methods=['GET'])
    # @transaction.atomic
    def groups(self, request, pk=None):
        entity = self.get_object()

        groups = EntityGroup.objects.filter(
            entity=entity
        ).select_related('group')

        return Response([
            {
                "id": g.group.id,
                "name": g.group.name
            }
            for g in groups
        ], status=status.HTTP_200_OK)



    @action(detail=True, methods=['POST'])
    @transaction.atomic
    def createGroup(self, request, pk=None):
        entity = self.get_object()

        name = request.data.get("name")
        if not name:
            return Response({"error": "name é obrigatório"}, status=400)

        group = Group.objects.create(name=name)

        # 🔥 Entity
        EntityGroup.objects.create(
            entity=entity,
            group=group
        )

        # 🔥 Propaga para sucursais
        sucursais = Branch.objects.filter(entity=entity)

        BranchGroup.objects.bulk_create([
            BranchGroup(branch=s, group=group)
            for s in sucursais
        ], ignore_conflicts=True)

        return Response({
            "id": group.id,
            "name": group.name
        })


    @action(detail=True, methods=['POST'])
    @transaction.atomic
    def addGroup(self, request, pk=None):
        entity = self.get_object()
        group_id = request.data.get("group")

        group = Group.objects.filter(id=group_id).first()
        if not group:
            return Response({"error": "Group not found"}, status=400)

        EntityGroup.objects.get_or_create(
            entity=entity,
            group=group
        )

        # 🔥 Propaga para sucursais
        sucursais = Branch.objects.filter(entity=entity)

        BranchGroup.objects.bulk_create([
            BranchGroup(branch=s, group=group)
            for s in sucursais
        ], ignore_conflicts=True)

        return Response({"success": True})


    @action(detail=True, methods=['POST'])
    @transaction.atomic
    def removeGroup(self, request, pk=None):
        entity = self.get_object()
        group_id = request.data.get("group")

        group = Group.objects.filter(id=group_id).first()
        if not group:
            return Response({"error": "Group not found"}, status=400)

        # 🔥 Remove da entity
        EntityGroup.objects.filter(
            entity=entity,
            group=group
        ).delete()

        # 🔥 Remove das sucursais
        BranchGroup.objects.filter(
            branch__entity=entity,
            group=group
        ).delete()

        BranchUserGroup.objects.filter(
            branch__entity=entity,
            group=group
        ).delete()

        return Response({"success": True})