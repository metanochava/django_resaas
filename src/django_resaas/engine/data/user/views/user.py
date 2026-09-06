import importlib
import importlib.util
from django.apps import apps

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django_resaas.engine.models.group import Group
from django_resaas.engine.models.user import User
from django_resaas.engine.models.entity import Entity
from django_resaas.engine.models.branch import Branch
from django_resaas.engine.models.entity_user import EntityUser
from django_resaas.engine.models.entity_app import EntityApp
from django_resaas.engine.models.entity_type_app import EntityTypeApp
from django_resaas.engine.models.branch_user import BranchUser
from django_resaas.engine.data.user.serializers.user import UserSerializer
from django_resaas.engine.data.entity.serializers.entity import EntitySerializer
from django_resaas.engine.data.branch.serializers.branch import BranchSerializer
from django_resaas.engine.models.branch_user_group import BranchUserGroup
from django_resaas.engine.data.person.serializers.person import PersonSerializer

from django.db import transaction

from django_resaas.engine.core.base.views import BaseAPIView



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
                        {"error": "Entity not found"},
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
                    {"error": "Entity not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 🔥 verifica se o user pertence à entidade
            pertence = EntityUser.objects.filter(
                user=instance,
                entity_id=entity_id
            ).exists()

            if not pertence:
                return Response(
                    {"error": "No permission to update this user"},
                    status=status.HTTP_403_FORBIDDEN
                )

        with transaction.atomic():

            # blocks manual entity change
            if not user.is_superuser and 'entity' in request.data:
                return Response(
                    {"error": "Not allowed to change entity"},
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

        # optional: prevent deleting yourself
        if instance == user:
            return Response(
                {"error": "Cannot delete your own user"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 👑 superuser pode tudo
        if not user.is_superuser:
            entity_id = getattr(request, "entity_id", None)

            if not entity_id:
                return Response(
                    {"error": "Entity not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # checks if the user belongs to the current entity
            pertence = EntityUser.objects.filter(
                user=instance,
                entity_id=entity_id
            ).exists()

            if not pertence:
                return Response(
                    {"error": "No permission to delete this user"},
                    status=status.HTTP_403_FORBIDDEN
                )

        # delete
        instance.delete()

        return Response(
            {"message": "User deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

    # @action(
    #     detail=True,
    #     methods=['GET'],
    # )
    # def userEntitys(self, request, id, *args, **kwargs):
    #     user = User.objects.get(id=id)
    #     user = UserSerializer(user)

    #     ar = []
    #     userEntitys = EntityUser.objects.filter(user__id=id, entity__entity_type__id=request.entity_type_id)
    #     if (userEntitys):
    #         for userEntity in userEntitys:
    #             entity = Entity.objects.get(id=userEntity.entity.id)
    #             entity = EntitySerializer(entity, context={'request': request})
    #             ar.append({'id': entity.data['id'], 'entityType': entity.data['entity_type'],  'name': entity.data['name'], 'created_at': entity.data['created_at'].split('-')[0], 'logo': entity.data['logo']})
           

    #     return Response(ar, status.HTTP_200_OK)


    @action(detail=True, methods=["GET"])
    def userEntitys(self, request, id, *args, **kwargs):
        user = User.objects.get(id=id)

        if not request.user.is_superuser and str(request.user.id) != str(user.id):
            return Response(
                {"detail": "You cannot access entities from another user."},
                status=status.HTTP_403_FORBIDDEN,
            )

        entities = Entity.objects.filter(
            Q(admins=user)
            | Q(entityuser__user=user, entityuser__deleted_at__isnull=True)
        ).select_related("entity_type").distinct().order_by("name")

        result = []

        for entity in entities:
            data = EntitySerializer(
                entity,
                context={"request": request},
            ).data

            result.append({
                "id": data["id"],
                "entityType": data["entity_type"],
                "name": data["name"],
                "created_at": (
                    data["created_at"].split("-")[0]
                    if data.get("created_at")
                    else None
                ),
                "logo": data.get("logo"),
            })

        return Response(result, status=status.HTTP_200_OK)

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
        add = {'alert_success':  '<b>' + branch.name+ '</b> was added successfully'}
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
        add = {'alert_success': '<b>' + branch.name+ '</b> was removed successfully'}
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

        user_perms = {
            str(permission).strip().lower()
            for permission in (user_perms or [])
            if permission
        }

        for item in menu_list:
            role = item.get("role")
            add_role = item.get("add_role")

            role = str(role).strip().lower() if role else None
            add_role = str(add_role).strip().lower() if add_role else None

            sub = self.filter_menu_by_permission(
                item.get("submenu", []),
                user_perms
            )

            has_perm = role is None or role in user_perms
            add_perm = add_role is None or add_role in user_perms

            if has_perm or sub:
                new = {
                    key: value
                    for key, value in item.items()
                    if key not in {"role", "add_role"}
                }

                if not add_perm:
                    new.pop("add_route", None)

                if sub:
                    new["submenu"] = sub
                else:
                    new.pop("submenu", None)

                result.append(new)

        return result


    @action(detail=True, methods=['GET'])
    def menus(self, request, *args, **kwargs):

        tipo_id = getattr(request, "entity_type_id", None)
        branch_id = getattr(request, "branch_id", None)
        group_id = getattr(request, "group_id", None)

        if not tipo_id:
            return Response([], status=status.HTTP_200_OK)

        # =====================================================
        # EFFECTIVE PERMISSIONS FOR CURRENT BRANCH/GROUP
        # =====================================================
        user_perms = set()

        if getattr(request.user, "is_superuser", False):
            # Superuser sees menu entries without being blocked by group roles.
            # Use all permission codenames so role checks continue to work.
            from django.contrib.auth.models import Permission

            user_perms = {
                str(codename).strip().lower()
                for codename in Permission.objects.values_list(
                    "codename",
                    flat=True
                )
            }

        elif branch_id and group_id:
            branch_user_group = (
                BranchUserGroup.objects
                .filter(
                    user_id=request.user.id,
                    branch_id=branch_id,
                    group_id=group_id
                )
                .select_related("group")
                .first()
            )

            if branch_user_group:
                user_perms = {
                    str(codename).strip().lower()
                    for codename in branch_user_group
                    .group
                    .permissions
                    .values_list("codename", flat=True)
                }

        # =====================================================
        # ACTIVE APPS FOR ENTITY TYPE
        # =====================================================
        apps_qs = (
            EntityTypeApp.objects
            .filter(entity_type_id=tipo_id)
            .select_related("app")
        )

        active_apps = {
            str(item.app.name).strip().lower()
            for item in apps_qs
            if item.app and item.app.name
        }

        def is_active_app(app_config):
            """
            Supports App.name values in any of these common forms:

                past.app
                app
                past
                django_resaas.hr
                hr

            Django AppConfig may expose:
                name  = full dotted Python path
                label = Django app label
            """

            app_name = str(app_config.name or "").strip().lower()
            app_label = str(app_config.label or "").strip().lower()

            parts = [
                part
                for part in app_name.split(".")
                if part
            ]

            candidates = {
                app_name,
                app_label,
            }

            if parts:
                candidates.add(parts[0])
                candidates.add(parts[-1])

            candidates.discard("")

            return bool(candidates.intersection(active_apps))

        # =====================================================
        # BUILD MENUS
        # =====================================================
        MENUS = []

        for app_config in apps.get_app_configs():

            if not is_active_app(app_config):
                continue

            module_name = f"{app_config.name}.sidebar"

            try:
                sidebar = importlib.import_module(module_name)

            except ModuleNotFoundError as exc:
                # Ignore only when this app has no sidebar.
                # If the sidebar exists but one of its internal imports fails,
                # re-raise the real error instead of hiding it.
                if exc.name == module_name:
                    continue
                raise

            ALL = getattr(sidebar, "ALL", [])

            print(ALL,'Alllll\n')

            for all_ in  ALL:
                print(all_, "meuuuuuuuuu\n")

                MENU = getattr(all_, "MENU", None)
                ICON = getattr(all_, "ICON", "menu")
                SUBMENUS = getattr(all_, "SUBMENUS", [])

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
                    "app": app_config.name,
                    "app_label": app_config.label,
                    "submenu": filtered_submenus,
                })

        return Response(MENUS, status=status.HTTP_200_OK)


    @action(
        detail=True,
        methods=['GET'],
    )
    def userPerson(self, request, id, *args, **kwargs):

        person = Person.objects.filter(user__id=id).first()

        if not person:
            return Response({}, status.HTTP_200_OK)

        serializer = PersonSerializer(person, context={'request': request})
        return Response(serializer.data, status.HTTP_200_OK)


    @action(
        detail=True,
        methods=['POST'],
    )
    def removeGroup(self, request, id ):
        user = User.objects.get(id=id)
        group_id = request.data['group']
        branchUserGroup = BranchUserGroup.objects.filter(user__id=id, branch__id=request.branch_id, group__id=group_id).first().delete()
        ar = []

        return Response(ar, status.HTTP_200_OK)



    @action(
        detail=True,
        methods=['POST'],
    )
    def addGroup(self, request, id):

        user = User.objects.get(id=id)

        group = Group.objects.get(id=request.data['group'])

        branch = Branch.objects.get(id=request.branch_id)

        branchUserGroup = BranchUserGroup.all_objects.filter(
            user_id=user.id,
            branch_id=branch.id,
            group_id=group.id
        ).first()

        if branchUserGroup:

            if branchUserGroup.deleted_at:

                branchUserGroup.deleted_at = None

                branchUserGroup.save(update_fields=['deleted_at'])

            message = 'Group linked successfully'

        else:

            branchUserGroup = BranchUserGroup.objects.create(
                user=user,
                group=group,
                branch=branch
            )

            message = 'Group added successfully'

        return Response(
            {
                'id': branchUserGroup.id,
                'user': str(user.id),
                'group': str(group.id),
                'branch': str(branch.id),
                'alert_success': message,
            },
            status=status.HTTP_200_OK
        )
