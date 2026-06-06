import importlib
import importlib.util
from django.apps import apps

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from django_resaas.models.group import Group
from django_resaas.models.user import User
from django_resaas.models.entity import Entity
from django_resaas.models.branch import Branch
from django_resaas.models.entity_user import EntityUser
from django_resaas.models.entity_app import EntityApp
from django_resaas.models.entity_type_app import EntityTypeApp
from django_resaas.models.branch_user import BranchUser
from django_resaas.data.user.serializers.user import UserSerializer
from django_resaas.data.entity.serializers.entity import EntitySerializer
from django_resaas.data.branch.serializers.branch import BranchSerializer
from django_resaas.models.branch_user_group import BranchUserGroup
from django_resaas.data.person.serializers.person import PersonSerializer

from django.db import transaction

from django_resaas.core.base.views import BaseAPIView



class UserAPIView(viewsets.ModelViewSet):
    search_fields = ['id','username']
    filter_backends = (filters.SearchFilter,)
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "id"

    # method_permission= {
    #     'userEntitys': 'view',
    #     'userBranchs': 'view',
    #     'userGroups': 'view',
    #     'permissions': 'view',
    #     'menus': 'view',
    # }

    def get_queryset(self):
        user = self.request.user

        queryset = User.objects.all().order_by('id')

        # 👑 superuser vê tudo
        if not user.is_superuser:
            entity_id = getattr(self.request, "entity_id", None)

            if not entity_id:
                return User.objects.none()  # segurança

            queryset = queryset.filter(
                entityuser__entity_id=entity_id
            ).distinct()

        return queryset
    
    # 🔥 override do list
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    
    
    def create(self, request, *args, **kwargs):
        user = request.user

        with transaction.atomic():

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_user = serializer.save()

            if not user.is_superuser:
                entity_id = getattr(request, "entity_id", None)

                if not entity_id:
                    return Response(
                        {"error": "Entity não encontrada"},
                        status=400
                    )

                EntityUser.objects.get_or_create(
                    user=new_user,
                    entity_id=entity_id
                )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

    

    def update(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()

        # 🔥 segurança: user normal só pode atualizar users da mesma entidade
        if not user.is_superuser:
            entity_id = getattr(request, "entity_id", None)

            if not entity_id:
                return Response(
                    {"error": "Entity não encontrada"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 🔥 verifica se o user pertence à entidade
            pertence = EntityUser.objects.filter(
                user=instance,
                entity_id=entity_id
            ).exists()

            if not pertence:
                return Response(
                    {"error": "Sem permissão para atualizar este user"},
                    status=status.HTTP_403_FORBIDDEN
                )

        with transaction.atomic():

            # 🔥 bloqueia alteração manual de entidade
            if not user.is_superuser and 'entity' in request.data:
                return Response(
                    {"error": "Não permitido alterar entidade"},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=kwargs.get('partial', False)
            )
            serializer.is_valid(raise_exception=True)
            updated_user = serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)



    def destroy(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()

        # 🔥 opcional: impedir apagar a si próprio
        if instance == user:
            return Response(
                {"error": "Não pode apagar o próprio utilizador"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 👑 superuser pode tudo
        if not user.is_superuser:
            entity_id = getattr(request, "entity_id", None)

            if not entity_id:
                return Response(
                    {"error": "Entity não encontrada"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 🔥 verifica se o user pertence à entidade corrente
            pertence = EntityUser.objects.filter(
                user=instance,
                entity_id=entity_id
            ).exists()

            if not pertence:
                return Response(
                    {"error": "Sem permissão para apagar este user"},
                    status=status.HTTP_403_FORBIDDEN
                )

        # 🔥 apagar
        instance.delete()

        return Response(
            {"message": "User apagado com sucesso"},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=True,
        methods=['GET'],
    )
    def userEntitys(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)
        user = UserSerializer(user)

        ar = []
        userEntitys = EntityUser.objects.filter(user__id=id, entity__entity_type__id=request.entity_type_id)
        if (userEntitys):
            for userEntity in userEntitys:
                entity = Entity.objects.get(id=userEntity.entity.id)
                entity = EntitySerializer(entity, context={'request': request})
                ar.append({'id': entity.data['id'], 'entityType': entity.data['entity_type'],  'name': entity.data['name'], 'created_at': entity.data['created_at'].split('-')[0], 'logo': entity.data['logo']})
           

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
    def userBranchs(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)
        user = UserSerializer(user)


        ar = []
        userBranchs = BranchUser.objects.filter(user__id=id, branch__entity__entity_type__id=request.entity_type_id, branch__entity__id=request.entity_id)
        if (userBranchs):
            for userBranch in userBranchs:
                branch = Branch.objects.get(id=userBranch.branch.id)
                branch = BranchSerializer(branch)
                ar.append({'id': branch.data['id'], 'name': branch.data['name']})

        return Response(ar, status.HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['POST'],
    )
    def addUserBranch(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)

        branch = Branch.objects.get(id= request.data['branch'])

        ar = []
        userBranchs = BranchUser.objects.filter(user__id=id, branch__id= branch.id,  branch__entity__entity_type__id=request.entity_type_id, branch__entity__id=request.entity_id)
        if (len(userBranchs) <= 1):
            su = BranchUser()
            su.user = user
            su.branch  = branch
            su.save()
            # data = json.loads(json.dumps(paciente.data, cls=DjangoJSONEncoder))
        add = {'alert_success':  '<b>' + branch.name+ '</b> foi adicionado com sucesso'}
            # data.update(add)
        return Response(add, status = status.HTTP_201_CREATED)
    
    @action(
        detail=True,
        methods=['POST'],
    )
    def removeUserBranch(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)
        branch = Branch.objects.get(id= request.data['branch'])

        userBranchs = BranchUser.objects.get(user__id=id, branch__id= branch.id, branch__entity__entity_type__id=request.entity_type_id, branch__entity__id=request.entity_id)
        userBranchs.delete()
        add = {'alert_success': '<b>' + branch.name+ '</b> foi removido com sucesso'}
        return Response(add, status = status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['GET'],
    )
    def userGroups(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)
        user = UserSerializer(user)

        if self.request.query_params.get('branch') == 'nulo' or self.request.query_params.get('branch') == None:
            pass
        else:
            branch_id = self.request.query_params.get('branch')

        branchUserGroups = BranchUserGroup.objects.filter(user__id=id, branch__id=request.branch_id)
        ar = []
        if (branchUserGroups):
            for branchUserGroup in branchUserGroups:
                group = Group.objects.get(id=branchUserGroup.group.id)
                ar.append({'id': group.id, 'name': group.name})

        if True:
            return Response(ar, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['GET'],
    )
    def permissions(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)

        user = UserSerializer(user)
        branchUserGroup = BranchUserGroup.objects.filter(user__id = id, branch__id=request.branch_id, group__id=request.group_id).first()
        
        per = []
        if (branchUserGroup):
            group = Group.objects.get(id=branchUserGroup.group.id)
            permissions = group.permissions.all()

            for permission in permissions:
                per.append({'id': permission.id, 'codename': permission.codename, 'name': permission.name})


        return Response(per, status.HTTP_200_OK)
  


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
                    new.pop("add_route", None)

                if sub:
                    new["submenu"] = sub

                result.append(new)

        return result



    @action(detail=True, methods=['GET'])
    def menus(self, request, *args, **kwargs):

        # ===============================
        # 🔥 PERMISSÕES DO USER
        # ===============================
        branchUserGroup = BranchUserGroup.objects.filter(
            user_id=request.user.id,
            branch_id=request.branch_id,
            group_id=request.group_id
        ).select_related('group')

        user_perms = []

        if branchUserGroup.exists():
            group = branchUserGroup.first().group
            user_perms = list(group.permissions.values_list('codename', flat=True))

        # ===============================
        # 🔥 TIPO ENTIDADE
        # ===============================
        tipo_id = getattr(request, "entity_type_id", None)

        if not tipo_id:
            return Response([], status=status.HTTP_200_OK)

        # ===============================
        # 🔥 MODULOS ATIVOS (AGORA CORRETO)
        # ===============================
        apps_qs = EntityTypeApp.objects.filter(
            entity_type_id=tipo_id
        ).select_related('app')

        names_apps = set(m.app.name for m in apps_qs)

        # ===============================
        # 🔥 GERAR MENUS
        # ===============================
        MENUS = []

        for app in apps.get_app_configs():

            if app.label not in names_apps:
                continue

            module_name = f"{app.name}.sidebar"

            try:
                sidebar = importlib.import_module(module_name)
            except ModuleNotFoundError:
                continue

            MENU = getattr(sidebar, "MENU", None)
            ICON = getattr(sidebar, "ICON", "menu")
            SUBMENUS = getattr(sidebar, "SUBMENUS", [])

            if not MENU or not SUBMENUS:
                continue

            filtered_submenus = self.filter_menu_by_permission(
                SUBMENUS,
                user_perms
            )

            if not filtered_submenus:
                continue

            MENUS.append({
                "menu": MENU,
                "icon": ICON,
                "submenu": filtered_submenus,
            })

        return Response(MENUS, status=status.HTTP_200_OK)
    


    @action(
        detail=True,
        methods=['GET'],
    )
    def userPerson(self, request, id, *args, **kwargs):

        person = Person.objects.get(user__id=id)
        person = PersonSerializer(person)
        if person:
            return Response(person.data, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)


    @action(
        detail=True,
        methods=['POST'],
    )
    def removeGroup(self, request, id ):
        user = User.objects.get(id=id)
        group_id = request.data['profile']['id']
        branch_id = request.data['branch_id']
        branchUserGroups = BranchUserGroup.objects.filter(user__id=id, branch__id=request.branch_id, group__id=request.group_id).first()
        branchUserGroups.delete()
        ar = []
        branchUserGroups = BranchUserGroup.objects.filter(user__id=id, branch__id=request.branch_id)
        if (branchUserGroups):
            for branchUserGroup in branchUserGroups:
                group = Group.objects.get(id=branchUserGroup.group.id)
                ar.append({'id': group.id, 'name': group.name})

        if True:
            return Response(ar, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)


    @action(
        detail=True,
        methods=['POST'],
    )
    def addGroup(self, request, id):
        user = User.objects.get(id=id)
        group_id = request.data['profile']['id']
        group = Group.objects.get(id=request.group_id)
        branch_id = request.data['branch_id']
        branch = Branch.objects.get(id=request.branch_id)
        branchUserGroups = BranchUserGroup.objects.filter(user__id=id, branch__id=request.branch_id, group__id=request.group_id).first()

        if None==branchUserGroups:
            branchUserGroup = BranchUserGroup()
            branchUserGroup.user = user
            branchUserGroup.group = group
            branchUserGroup.branch = branch
            branchUserGroup.save()
        branchUserGroups = BranchUserGroup.objects.filter(user__id=id, branch__id=request.branch_id)

        ar = []
        if (branchUserGroups):
            for branchUserGroup in branchUserGroups:
                group = Group.objects.get(id=branchUserGroup.group.id)
                ar.append({'id': group.id, 'name': group.name})


        if True:
            return Response(ar, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)







    