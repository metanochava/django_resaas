# =========================
# Python standard library
# =========================
import base64
import os
import random


# =========================
# Third-party
# =========================
import barcode
import qrcode
from barcode.writer import ImageWriter
from PIL import Image


# =========================
# Django
# =========================
from django.conf import settings


# =========================
# Django REST Framework
# =========================
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


# =========================
# Local application (absolute imports)
# =========================
from django_resaas.engine.core.utils.translate import Translate
from django_resaas.engine.core.services.disc_manager import DiskManegarService

from django_resaas.engine.models.entity import Entity
from django_resaas.engine.models.file import File
from django_resaas.engine.models.branch import Branch
from django_resaas.engine.models.branch_user_group import BranchUserGroup

from django_resaas.engine.data.branch.serializers.branch import BranchSerializer
from django_resaas.engine.data.entity.serializers.entity import EntitySerializer
from django_resaas.engine.data.file.serializers.file import FileSerializer
from django_resaas.engine.data.file.serializers.file_gravar import FileGravarSerializer






class  BranchAPIView(viewsets.ModelViewSet):
    #permission_classes = (permissions.IsAuthenticated)
    search_fields = ['id','name']
    filter_backends = (filters.SearchFilter,)
    
    serializer_class = BranchSerializer
    queryset = Branch.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user

        queryset = self.queryset.order_by('-id')

        # 👑 superuser vê tudo
        if user.is_superuser:
            return queryset

        # 👤 user normal → filtra por entidade
        entity_id = getattr(self.request, "entity_id", None)

        if not entity_id:
            return Branch.objects.none()

        return queryset.filter(entity_id=entity_id)

    @action(
        detail=True,
        methods=['GET'],
    )
    def groups(self, request, id):
        branchUserGroups = BranchUserGroup.objects.all().filter(branch__id=id, user__id=request.user.id)
        suc = []
        for branchUserGroup in branchUserGroups:
            suc.append({'id': branchUserGroup.group.id, 'name': branchUserGroup.group.name})

        return Response(suc)

    @action(
        detail=True,
        methods=['GET'],
    )
    def Url(self, request, id):
        branch = Branch.objects.get(id=id)
        entity = Entity.objects.get(id=branch.entity.id)
        return Response(str(entity.entity_type.id)+'/'+str(branch.entity.id)+'/'+str(branch.id))
    
    

    @action(
        detail=True,
        methods=['GET'],
    )
    def getCapasSite(self, request, id):
        files = Files.objects.filter(branch__id=id, funcionalidade='Cover')
        files = FileSerializer(files, many=True)
        data = (files.data)
        return Response(data, status=status.HTTP_200_OK)
    

    @action(
        detail=True,
        methods=['POST'],
    )
    def postCapasSite(self, request, id):
        branch = Branch.objects.get(id=id)

        request.data['entity'] = str(branch.entity.id)
        request.data['branch'] = str(branch.id)
        uploaded_file = request.FILES['file']

        if DiskManegarService.freeSpace(branch.entity.id, request.FILES['file']):
            resposta = {'alert_error': 'Unable to upload file<br><b>Contact the administrator</b>'}
            return Response(resposta , status=status.HTTP_400_BAD_REQUEST)

        request.data['size'] = uploaded_file.size
        request.data['model'] = 'branch'
        request.data['state'] = 1
        request.data['funcionalidade'] = 'Cover'

        file = FileGravarSerializer(data=request.data)
        if file.is_valid(raise_exception=True):
            file.save()
            file = FileSerializer(Files.objects.get(id=file.data['id']))
            DiskManegarService.updateSpace(branch.entity.id, request.FILES['file'])
            return Response(file.data, status=status.HTTP_201_CREATED)
        else:
            return Response(file.errors, status=status.HTTP_400_BAD_REQUEST)
        
    

    @action(
        detail=True,
        methods=['GET'],
    )
    def qr(self, request, id):
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

        pk = id


        template_path = 'core/branch/qr_pdf.html'

        branch = Branch.objects.get(id=pk)
        branch1 = branch

    

        entity = EntitySerializer(branch.entity)

        branch = BranchSerializer(branch)
        file  = Files.objects.get(entity = branch1.entity.id, funcionalidade = 'Logo')
        logo_name = file.file.path
        try:
            file = open(logo_name, 'rb').read()
            logo = base64.b64encode(bytes(file))
        except Exception as e:
            logo = logo_name.split('.')[-1]
    
        
        url = origin + '/#/?s=' + branch.data['id'] + '&q=1' 
        var_qr['entity'] = entity.data['name']
        var_qr['branch'] = branch.data['name']
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
            'branch': branch.data,
            'logo':logo,
            'titulo': Translate.tdc(lingua, 'QR'),
            'name': Translate.tdc(lingua, 'Branch'),
            'de': Translate.tdc(lingua, 'of'),
            'morada': Translate.tdc(lingua, 'Address'),
            'pagina': Translate.tdc(lingua, 'Page')
        }

        return Response(context, status=status.HTTP_200_OK)

