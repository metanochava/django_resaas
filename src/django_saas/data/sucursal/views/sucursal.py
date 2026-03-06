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
from django_saas.core.utils.translate import Translate
from django_saas.core.services.disc_manager import DiskManegarService

from django_saas.models.entidade import Entidade
from django_saas.models.ficheiro import Ficheiro
from django_saas.models.sucursal import Sucursal
from django_saas.models.sucursal_user_group import SucursalUserGroup

from django_saas.data.sucursal.serializers.sucursal import SucursalSerializer
from django_saas.data.entidade.serializers.entidade import EntidadeSerializer
from django_saas.data.ficheiro.serializers.ficheiro import FicheiroSerializer
from django_saas.data.ficheiro.serializers.ficheiro_gravar import FicheiroGravarSerializer






class  SucursalAPIView(viewsets.ModelViewSet):
    #permission_classes = (permissions.IsAuthenticated)
    search_fields = ['id','nome']
    filter_backends = (filters.SearchFilter,)
    
    serializer_class = SucursalSerializer
    queryset = Sucursal.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

    @action(
        detail=True,
        methods=['GET'],
    )
    def grupos(self, request, id):
        sucursalUserGroups = SucursalUserGroup.objects.all().filter(sucursal__id=id, user__id=request.user.id)
        suc = []
        for sucursalUserGroup in sucursalUserGroups:
            suc.append({'id': sucursalUserGroup.group.id, 'name': sucursalUserGroup.group.name})

        return Response(suc)

    @action(
        detail=True,
        methods=['GET'],
    )
    def Url(self, request, id):
        sucursal = Sucursal.objects.get(id=id)
        entidade = Entidade.objects.get(id=sucursal.entidade.id)
        return Response(str(entidade.tipo_entidade.id)+'/'+str(sucursal.entidade.id)+'/'+str(sucursal.id))
    
    

    @action(
        detail=True,
        methods=['GET'],
    )
    def getCapasSite(self, request, id):
        ficheiros = Ficheiros.objects.filter(sucursal__id=id, funcionalidade='CapaSite')
        ficheiros = FicheiroSerializer(ficheiros, many=True)
        data = (ficheiros.data)
        return Response(data, status=status.HTTP_200_OK)
    

    @action(
        detail=True,
        methods=['POST'],
    )
    def postCapasSite(self, request, id):
        sucursal = Sucursal.objects.get(id=id)

        request.data['entidade'] = str(sucursal.entidade.id)
        request.data['sucursal'] = str(sucursal.id)
        uploaded_file = request.FILES['ficheiro']

        if DiskManegarService.freeSpace(sucursal.entidade.id, request.FILES['ficheiro']):
            resposta = {'alert_error': 'Nao e possivel fazer upload de ficheiro<br><b>Contacte o adminstrador</b>'}
            return Response(resposta , status=status.HTTP_400_BAD_REQUEST)

        request.data['size'] = uploaded_file.size
        request.data['modelo'] = 'sucursal'
        request.data['estado'] = 'Activo'
        request.data['funcionalidade'] = 'CapaSite'

        ficheiro = FicheiroGravarSerializer(data=request.data)
        if ficheiro.is_valid(raise_exception=True):
            ficheiro.save()
            ficheiro = FicheiroSerializer(Ficheiros.objects.get(id=ficheiro.data['id']))
            DiskManegarService.updateSpace(sucursal.entidade.id, request.FILES['ficheiro'])
            return Response(ficheiro.data, status=status.HTTP_201_CREATED)
        else:
            return Response(ficheiro.errors, status=status.HTTP_400_BAD_REQUEST)
        
    

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

        pk = id


        template_path = 'core/sucursal/qr_pdf.html'

        sucursal = Sucursal.objects.get(id=pk)
        sucursal1 = sucursal

    

        entidade = EntidadeSerializer(sucursal.entidade)

        sucursal = SucursalSerializer(sucursal)
        ficheiro  = Ficheiros.objects.get(entidade = sucursal1.entidade.id, funcionalidade = 'Logo')
        logo_name = ficheiro.ficheiro.path
        try:
            file = open(logo_name, 'rb').read()
            logo = base64.b64encode(bytes(file))
        except Exception as e:
            logo = logo_name.split('.')[-1]
        print(logo, logo_name, ficheiro)
        
        url = origin + '/#/?s=' + sucursal.data['id'] + '&q=1' 
        var_qr['entidade'] = entidade.data['nome']
        var_qr['sucursal'] = sucursal.data['nome']
        for key, value in var_qr.items():
            url = url + '&' + key + '=' + value
        # print(url)
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
            'sucursal': sucursal.data,
            'logo':logo,
            'titulo': Translate.tdc(lingua, 'QR'),
            'nome': Translate.tdc(lingua, 'Sucursal'),
            'de': Translate.tdc(lingua, 'de'),
            'morada': Translate.tdc(lingua, 'Morada'),
            'pagina': Translate.tdc(lingua, 'Pagina')
        }

        return Response(context, status=status.HTTP_200_OK)

