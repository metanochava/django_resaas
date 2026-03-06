import importlib
import importlib.util
from django.apps import apps

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from django.contrib.auth.models import Group
from django_saas.models.user import User
from django_saas.models.entidade import Entidade
from django_saas.models.sucursal import Sucursal
from django_saas.models.entidade_user import EntidadeUser
from django_saas.models.entidade_modulo import EntidadeModulo
from django_saas.models.tipo_entidade_modulo import TipoEntidadeModulo
from django_saas.models.sucursal_user import SucursalUser
from django_saas.data.user.serializers.user import UserSerializer
from django_saas.data.entidade.serializers.entidade import EntidadeSerializer
from django_saas.data.sucursal.serializers.sucursal import SucursalSerializer
from django_saas.models.sucursal_user_group import SucursalUserGroup




class UserAPIView(viewsets.ModelViewSet):
    search_fields = ['id','username']
    filter_backends = (filters.SearchFilter,)
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        if (self.request.query_params.get('allPaginado')):
            return self.queryset.filter().order_by('id')
        else:
            self._paginator = None
            return self.queryset.filter().order_by('id')

    @action(
        detail=True,
        methods=['GET'],
    )
    def userEntidades(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)
        user = UserSerializer(user)

        ar = []
        userEntidades = EntidadeUser.objects.filter(user__id=id, entidade__tipo_entidade__id=request.tipo_entidade_id)
        if (userEntidades):
            for userEntidade in userEntidades:
                entidade = Entidade.objects.get(id=userEntidade.entidade.id)
                entidade = EntidadeSerializer(entidade, context={'request': request})
                ar.append({'id': entidade.data['id'], 'tipoEntidade': entidade.data['tipo_entidade'],  'nome': entidade.data['nome'], 'created_at': entidade.data['created_at'].split('-')[0], 'logo': entidade.data['logo']})
           

        return Response(ar, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['GET'],
    )
    def logins(self, request, id, *args, **kwargs):
        userLogin = UserLogin.objects.filter(user_id = id).order_by('-data', 'hora')
        userLogins = LoginSerializer(userLogin, many=True)
        return Response(userLogins.data, status=status.HTTP_200_OK)
    
    
    @action(
        detail=True,
        methods=['GET'],
    )
    def userSucursals(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)
        user = UserSerializer(user)


        ar = []
        userSucursals = SucursalUser.objects.filter(user__id=id, sucursal__entidade__tipo_entidade__id=request.tipo_entidade_id, sucursal__entidade__id=request.entidade_id)
        if (userSucursals):
            for userSucursal in userSucursals:
                sucursal = Sucursal.objects.get(id=userSucursal.sucursal.id)
                sucursal = SucursalSerializer(sucursal)
                ar.append({'id': sucursal.data['id'], 'nome': sucursal.data['nome']})

        return Response(ar, status.HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['POST'],
    )
    def addUserSucursal(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)

        sucursal = Sucursal.objects.get(id= request.data['sucursal'])

        ar = []
        userSucursals = SucursalUser.objects.filter(user__id=id, sucursal__id= sucursal.id,  sucursal__entidade__tipo_entidade__id=request.tipo_entidade_id, sucursal__entidade__id=request.entidade_id)
        if (len(userSucursals) <= 1):
            su = SucursalUser()
            su.user = user
            su.sucursal  = sucursal
            su.save()
            # data = json.loads(json.dumps(paciente.data, cls=DjangoJSONEncoder))
        add = {'alert_success':  '<b>' + sucursal.nome+ '</b> foi adicionado com sucesso'}
            # data.update(add)
        return Response(add, status = status.HTTP_201_CREATED)
    
    @action(
        detail=True,
        methods=['POST'],
    )
    def removeUserSucursal(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)
        sucursal = Sucursal.objects.get(id= request.data['sucursal'])

        userSucursals = SucursalUser.objects.get(user__id=id, sucursal__id= sucursal.id, sucursal__entidade__tipo_entidade__id=request.tipo_entidade_id, sucursal__entidade__id=request.entidade_id)
        userSucursals.delete()
        add = {'alert_success': '<b>' + sucursal.nome+ '</b> foi removido com sucesso'}
        return Response(add, status = status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['GET'],
    )
    def userGrupos(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)
        user = UserSerializer(user)

        if self.request.query_params.get('sucursal') == 'nulo' or self.request.query_params.get('sucursal') == None:
            pass
        else:
            sucursal_id = self.request.query_params.get('sucursal')

        sucursalUserGroups = SucursalUserGroup.objects.filter(user__id=id, sucursal__id=request.sucursal_id)
        ar = []
        if (sucursalUserGroups):
            for sucursalUserGroup in sucursalUserGroups:
                group = Group.objects.get(id=sucursalUserGroup.group.id)
                ar.append({'id': group.id, 'name': group.name})

        if True:
            return Response(ar, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['GET'],
    )
    def userPermicoes(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)
        user = UserSerializer(user)
        sucursalUserGroup = SucursalUserGroup.objects.filter(user__id = id, sucursal__id=request.sucursal_id, group__id=request.group_id)
        
        per = []
        if (sucursalUserGroup):
            grupo = Group.objects.get(id=sucursalUserGroup[0].group.id)
            permissions = grupo.permissions.all()

            for permission in permissions:
                per.append({'id': permission.id, 'codename': permission.codename, 'name': permission.name})

        if True:
            return Response(per, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)


    def filter_menu_by_permission(self, menu_list, user_perms):
        result = []

        for item in menu_list:
            role = item.get("role")
            add_role = item.get("add_role")

            # Filtra submenus
            sub = self.filter_menu_by_permission(item.get("submenu", []), user_perms)

            has_perm = role is None or role in user_perms
            add_perm = add_role is None or add_role in user_perms

            if has_perm or sub:
                new = {k: v for k, v in item.items() if k not in {"role", "add_role"}}

                if not add_perm:
                    new.pop("add_rota", None)

                if sub:
                    new["submenu"] = sub

                result.append(new)

        return result


    @action(detail=True, methods=['GET'])
    def menus(self, request, *args, **kwargs):
        sucursalUserGroup = SucursalUserGroup.objects.filter(user__id = request.user.id, sucursal__id=request.sucursal_id, group__id=request.group_id)
        user_perms = []
        if (sucursalUserGroup):
            grupo = Group.objects.get(id=sucursalUserGroup[0].group.id)
            permissions = grupo.permissions.all()
            for permission in permissions:
                user_perms.append(permission.codename)

        MENUS = []
      

        for app in apps.get_app_configs():
            module_name = f"{app.name}.sidebar"
            if not EntidadeModulo.objects.filter(entidade__id=request.entidade_id, modulo__nome=app.label, modulo__estado=1, estado=1).exists():
                continue

            if not importlib.util.find_spec(module_name):
                continue

            sidebar = importlib.import_module(module_name)

            # Filtrar submenus recursivamente
            filtered_submenus = self.filter_menu_by_permission(
                sidebar.SUBMENUS,
                user_perms
            )
    
            # Se não tem submenu permitido → ignora menu
            if not filtered_submenus:
                continue

            MENUS.append({
                "menu": sidebar.MENU,
                "icon": sidebar.ICON,
                "submenu": filtered_submenus,
            })

        return Response(MENUS, status=status.HTTP_200_OK)


    @action(
        detail=True,
        methods=['GET'],
    )
    def userPessoa(self, request, id, *args, **kwargs):

        pessoa = Pessoa.objects.get(user__id=id)
        pessoa = PessoaSerializer(pessoa)
        if pessoa:
            return Response(pessoa.data, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)


    @action(
        detail=True,
        methods=['POST'],
    )
    def removerPerfil(self, request, id ):
        user = User.objects.get(id=id)
        group_id = request.data['perfil']['id']
        sucursal_id = request.data['sucursal_id']
        sucursalUserGroups = SucursalUserGroup.objects.filter(user__id=id, sucursal__id=request.sucursal_id, group__id=request.group_id).first()
        sucursalUserGroups.delete()
        ar = []
        sucursalUserGroups = SucursalUserGroup.objects.filter(user__id=id, sucursal__id=request.sucursal_id)
        if (sucursalUserGroups):
            for sucursalUserGroup in sucursalUserGroups:
                group = Group.objects.get(id=sucursalUserGroup.group.id)
                ar.append({'id': group.id, 'name': group.name})


        if True:
            return Response(ar, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)


    @action(
        detail=True,
        methods=['POST'],
    )
    def adicionarPerfil(self, request, id):
        user = User.objects.get(id=id)
        group_id = request.data['perfil']['id']
        group = Group.objects.get(id=request.group_id)
        sucursal_id = request.data['sucursal_id']
        sucursal = Sucursal.objects.get(id=request.sucursal_id)
        sucursalUserGroups = SucursalUserGroup.objects.filter(user__id=id, sucursal__id=request.sucursal_id, group__id=request.group_id).first()

        if None==sucursalUserGroups:
            sucursalUserGroup = SucursalUserGroup()
            sucursalUserGroup.user = user
            sucursalUserGroup.group = group
            sucursalUserGroup.sucursal = sucursal
            sucursalUserGroup.save()
        sucursalUserGroups = SucursalUserGroup.objects.filter(user__id=id, sucursal__id=request.sucursal_id)

        ar = []
        if (sucursalUserGroups):
            for sucursalUserGroup in sucursalUserGroups:
                group = Group.objects.get(id=sucursalUserGroup.group.id)
                ar.append({'id': group.id, 'name': group.name})


        if True:
            return Response(ar, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)


