import importlib
import importlib.util
from django.apps import apps

from rest_framework import viewsets, filters, status
from django_resaas.saas.core.exceptions import error_response
from django_resaas.saas.core.decorators.action import resaas_action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django_resaas.saas.models.group import Group
from django_resaas.saas.models.user import User
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.layout_setting import LayoutSetting
from django_resaas.saas.data.user.serializers.me import MeSerializer
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.entity_app import EntityApp
from django_resaas.saas.models.entity_type_app import EntityTypeApp
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.data.user.serializers.user import UserSerializer
from django_resaas.saas.data.entity.serializers.entity import EntitySerializer
from django_resaas.saas.data.branch.serializers.branch import BranchSerializer
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.user_login import UserLogin
from django_resaas.saas.core.base.permissions import isPermited
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.core.services import temporary_password_service, two_factor_service
from django_resaas.saas.core.services.temporary_password_service import TemporaryPasswordError
from django_resaas.saas.models.user_temporary_password import UserTemporaryPassword
from django_resaas.saas.data.person.serializers.person import PersonSerializer
from django_resaas.saas.models.person import Person

from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError

from django_resaas.saas.core.base.views import BaseAPIView



class UserAPIView(viewsets.ModelViewSet):
    search_fields = ['id','username']
    filter_backends = (filters.SearchFilter,)
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "id"

    # Everything here needs a signed-in user. This ViewSet used to run with no
    # permission classes at all (DEFAULT_PERMISSION_CLASSES is empty), so its
    # custom actions answered anonymous requests.
    permission_classes = [IsAuthenticated]

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

    # @resaas_action(
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


    @resaas_action(detail=True, methods=["GET"])
    def userEntitys(self, request, id, *args, **kwargs):
        try:
            user = User.objects.filter(pk=id).first()
        except (ValueError, DjangoValidationError):
            user = None

        if user is None:
            return self._group_error(request, "user_not_found", "User not found.", status.HTTP_404_NOT_FOUND)

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
                # entity_type ({id, value, label}) is what every frontend
                # consumer of the selected Entity reads (the home dashboards
                # pick the module from it). entityType is the old key, kept
                # for compatibility (DEPRECATED).
                "entity_type": data["entity_type"],
                "entityType": data["entity_type"],
                "name": data["name"],
                "dashboard": data["dashboard"],
                "created_at": (
                    data["created_at"].split("-")[0]
                    if data.get("created_at")
                    else None
                ),
                "logo": data.get("logo"),
            })

        return Response(result, status=status.HTTP_200_OK)

    @resaas_action(
        detail=True,
        methods=['GET'],
    )
    def logins(self, request, id, *args, **kwargs):
        target, error = self._self_or_secure(request, id, 'view_user')
        if error:
            return error

        logins = UserLogin.objects.filter(user_id=target.id).order_by('-created_at')[:30]

        return Response(
            [{'device': login.dispositivo or '', 'created_at': login.created_at} for login in logins],
            status=status.HTTP_200_OK,
        )
    
    
    @resaas_action(
        detail=True,
        methods=['GET'],
    )
    def userBranchs(self, request, id, *args, **kwargs):
        target, error = self._self_or_secure(request, id, 'view_user')
        if error:
            return error


        ar = []
        userBranchs = BranchUser.objects.filter(user__id=id, branch__entity__entity_type__id=request.entity_type_id, branch__entity__id=request.entity_id)
        if (userBranchs):
            for userBranch in userBranchs:
                branch = Branch.objects.get(id=userBranch.branch.id)
                branch = BranchSerializer(branch)
                ar.append({'id': branch.data['id'], 'name': branch.data['name']})

        return Response(ar, status.HTTP_200_OK)
    
    @resaas_action(
        detail=True,
        methods=['POST'],
    )
    def addUserBranch(self, request, id, *args, **kwargs):
        # changing WHICH branches a user belongs to is an administrative act:
        # permission + entity scope, never a self-service shortcut
        user, error = self._secure_target(request, id, 'change_user')
        if error:
            return error

        branch = Branch.objects.filter(id=request.data.get('branch'), entity_id=request.entity_id).first() \
            if request.data.get('branch') else None

        if branch is None:
            return self._group_error(request, "branch_not_found", "Branch not found.", status.HTTP_404_NOT_FOUND)

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
    
    @resaas_action(
        detail=True,
        methods=['POST'],
    )
    def removeUserBranch(self, request, id, *args, **kwargs):
        user, error = self._secure_target(request, id, 'change_user')
        if error:
            return error

        branch = Branch.objects.filter(id=request.data.get('branch'), entity_id=request.entity_id).first() \
            if request.data.get('branch') else None
        userBranchs = BranchUser.objects.filter(user__id=id, branch__id=branch.id if branch else None).first()

        if branch is None or userBranchs is None:
            return self._group_error(request, "branch_not_found", "Branch not found.", status.HTTP_404_NOT_FOUND)

        userBranchs.delete()
        add = {'alert_success': '<b>' + branch.name+ '</b> was removed successfully'}
        return Response(add, status = status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # Who may act on `id`: the user themselves (own data needs no permission -
    # it is how the login flow works before any profile is active), or someone
    # holding the permission AND sharing the entity (see _secure_target).
    # ------------------------------------------------------------------

    def _self_or_secure(self, request, id, permission):
        """Returns (target_user, error_response). Exactly one is not None."""
        if str(id) == str(request.user.id):
            return request.user, None

        return self._secure_target(request, id, permission)

    # ------------------------------------------------------------------
    # GROUP ASSIGNMENT (userGroups / addGroup / removeGroup)
    #
    # The assignment IS a BranchUserGroup row (branch, user, group): the
    # branch always comes from the signed tenant context (request.branch_id),
    # never from the request body. These three actions used to run with no
    # authentication or authorization at all (this ViewSet is not a
    # BaseAPIView and DEFAULT_PERMISSION_CLASSES is empty), accepted any
    # Group id (including groups the Entity does not own, e.g. Root) and any
    # user id. They now enforce, on the backend:
    #
    #   authenticated  +  tenant context  +  permission  +  tenant scope
    #
    # The permission is the one of the model that really represents the
    # assignment (BranchUserGroup: list_/add_/delete_branchusergroup - the
    # existing, already-synchronised model permissions, declared below with
    # @resaas_action(permission=...) so declaration and enforcement share one
    # source). The URLs and success payloads are unchanged.
    # ------------------------------------------------------------------

    def _group_error(self, request, code, message, http_status):
        # stable machine code + translated human message
        return error_response(request, message, http_status, code=code)

    def _group_assignment_guard(self, request, id, allow_self=False):
        """Returns (target_user, error_response). Exactly one is not None.

        allow_self: a user may always read THEIR OWN profiles of the current
        branch without any permission - that is how the login flow lists the
        profiles to pick from (GroupStore.getGroups), before any profile is
        even active. Everything about OTHER users needs the permission."""
        if not request.user or not request.user.is_authenticated:
            return None, self._group_error(request, "authentication_required", "Authentication required.", status.HTTP_401_UNAUTHORIZED)

        reading_own = allow_self and str(id) == str(request.user.id)

        if not getattr(request, "entity_id", None) or not getattr(request, "branch_id", None):
            if reading_own:
                # nothing selected yet -> nothing assigned (as before)
                return request.user, Response([], status.HTTP_200_OK)

            return None, self._group_error(request, "tenant_context_required", "RESAAS context is required.", status.HTTP_403_FORBIDDEN)

        permission = getattr(self, self.action)._resaas_action["permission"]

        if not reading_own and not isPermited(request=request, role=permission):
            return None, self._group_error(request, "permission_denied", "Permission denied", status.HTTP_403_FORBIDDEN)

        try:
            target = User.objects.filter(pk=id).first()
        except (ValueError, DjangoValidationError):
            target = None

        if target is None:
            return None, self._group_error(request, "user_not_found", "User not found.", status.HTTP_404_NOT_FOUND)

        return target, None

    def _is_entity_member(self, request, user):
        return EntityUser.objects.filter(entity_id=request.entity_id, user_id=user.id).exists()

    def _entity_group_or_error(self, request, raw_group_id):
        """The Group, only if the CURRENT Entity owns it (EntityGroup)."""
        try:
            group = Group.objects.filter(
                pk=raw_group_id,
                entitygroup__entity_id=request.entity_id,
            ).first()
        except (ValueError, TypeError, DjangoValidationError):
            group = None

        if group is None:
            return None, self._group_error(request, "group_not_in_entity", "This profile does not belong to the current entity.", status.HTTP_404_NOT_FOUND)

        return group, None

    @resaas_action(
        detail=True,
        methods=['GET'],
        permission='list_branchusergroup',
    )
    def userGroups(self, request, id, *args, **kwargs):
        target, error = self._group_assignment_guard(request, id, allow_self=True)
        if error:
            return error

        # a user outside the current Entity has no assignments in it
        if str(target.id) != str(request.user.id) and not self._is_entity_member(request, target):
            return Response([], status.HTTP_200_OK)

        assignments = (
            BranchUserGroup.objects
            .filter(user_id=target.id, branch_id=request.branch_id)
            .select_related('group')
            .order_by('group__name')
        )

        return Response(
            [
                {'id': item.group.id, 'name': item.group.name, 'state': item.state}
                for item in assignments
            ],
            status.HTTP_200_OK,
        )

    @resaas_action(
        detail=True,
        methods=['GET'],
    )
    def permissions(self, request, id, *args, **kwargs):
        target, error = self._self_or_secure(request, id, 'view_user')
        if error:
            return error

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


    @resaas_action(detail=True, methods=['GET'])
    def menus(self, request, *args, **kwargs):

        tipo_id = getattr(request, "entity_type_id", None)
        branch_id = getattr(request, "branch_id", None)
        group_id = getattr(request, "group_id", None)

        if not tipo_id:
            return Response([], status=status.HTTP_200_OK)

        # =====================================================
        # EFFECTIVE PERMISSIONS FOR CURRENT BRANCH/GROUP
        #
        # Deliberadamente SEM bypass de is_superuser aqui: o menu
        # reflecte sempre o grupo/perfil actualmente seleccionado
        # (BranchUserGroup), mesmo para superuser. Sem isto, trocar o
        # perfil activo para "Guest" (BootstrapService já associa o
        # criador da entity a "Guest" além do grupo admin escolhido,
        # precisamente para servir de pré-visualização) nunca mudava o
        # menu de um superuser - via sempre tudo, independentemente do
        # perfil seleccionado. Um superuser continua a ver tudo nas
        # entities/branches onde estiver em "Root" (que já tem todas
        # as permissões via create_model_permissions), sem precisar de
        # nenhum caso especial aqui.
        # =====================================================
        user_perms = set()

        if branch_id and group_id:
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

            if not isinstance(ALL, (list, tuple)):
                continue

            for menu_config in ALL:

                if not isinstance(menu_config, dict):
                    continue

                MENU = menu_config.get("MENU")
                ICON = menu_config.get("ICON", "menu")
                SUBMENUS = menu_config.get("SUBMENUS", [])

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


    # ==========================================================
    # 🔀 PERSONAL LAYOUT FIELD TOGGLE (generic)
    #
    # Shared by toggle_menu_rtl and toggle_sidebar_mini below - both are
    # a single boolean field living exclusively in LayoutSetting (User >
    # Entity > EntityType, ver User.get_effective_layout()), toggled the
    # exact same way: flip it on the user's own override if they already
    # have one, otherwise fork a personal copy of the effective
    # (Entity/EntityType) LayoutSetting with just that field flipped, so
    # the rest of the inherited configuration (sidebar/header/footer/
    # etc.) - and any OTHER tenant using that same shared LayoutSetting
    # - is never mutated. Always over request.user (never another id),
    # so every caller stays detail=False.
    # ==========================================================

    def _toggle_personal_layout_field(self, request, field_name):
        user = request.user

        entity = Entity.objects.filter(
            id=getattr(request, 'entity_id', None)
        ).first()

        effective = user.get_effective_layout(entity)
        current_value = getattr(effective, field_name, False) if effective else False

        if user.layout_settings:
            setattr(user.layout_settings, field_name, not current_value)
            user.layout_settings.save(update_fields=[field_name])

        else:
            copyable_fields = [
                f.name for f in LayoutSetting._meta.fields
                if f.name not in (
                    'id', 'created_at', 'updated_at', 'deleted_at',
                    'created_by', 'updated_by', 'state',
                )
            ]

            data = (
                {name: getattr(effective, name) for name in copyable_fields}
                if effective else {}
            )

            data[field_name] = not current_value
            data['state'] = 'Active'

            new_layout = LayoutSetting.objects.create(**data)

            user.layout_settings = new_layout
            user.save(update_fields=['layout_settings'])

        return Response(
            MeSerializer(user, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )

    # menu_rtl vive exclusivamente em LayoutSetting - ver
    # _toggle_personal_layout_field() acima.
    @resaas_action(detail=False, methods=['POST'])
    def toggle_menu_rtl(self, request, *args, **kwargs):
        return self._toggle_personal_layout_field(request, 'menu_rtl')

    # sidebar_mini idem - ver _toggle_personal_layout_field() acima.
    @resaas_action(detail=False, methods=['POST'])
    def toggle_sidebar_mini(self, request, *args, **kwargs):
        return self._toggle_personal_layout_field(request, 'sidebar_mini')

    @resaas_action(
        detail=True,
        methods=['GET'],
    )
    def userPerson(self, request, id, *args, **kwargs):
        target, error = self._self_or_secure(request, id, 'view_user')
        if error:
            return error

        person = Person.objects.filter(user__id=target.id).first()

        if not person:
            return Response({}, status.HTTP_200_OK)

        serializer = PersonSerializer(person, context={'request': request})
        return Response(serializer.data, status.HTTP_200_OK)


    @resaas_action(
        detail=True,
        methods=['POST'],
        permission='delete_branchusergroup',
    )
    def removeGroup(self, request, id):
        target, error = self._group_assignment_guard(request, id)
        if error:
            return error

        group_id = request.data.get('group')

        # never lock yourself out of the profile you are acting with
        if str(target.id) == str(request.user.id) and str(group_id) == str(request.group_id):
            return self._group_error(request, "cannot_remove_own_active_group", "You cannot remove the profile you are currently using.", status.HTTP_400_BAD_REQUEST)

        try:
            assignment = BranchUserGroup.objects.filter(
                user_id=target.id,
                branch_id=request.branch_id,
                group_id=group_id,
            ).first()
        except (ValueError, TypeError, DjangoValidationError):
            assignment = None

        if assignment is None or not self._is_entity_member(request, target):
            return self._group_error(request, "group_not_assigned", "This profile is not assigned to the user.", status.HTTP_404_NOT_FOUND)

        # only the assignment goes - never the Group, EntityGroup, user or
        # the same group's assignment in another branch/entity
        assignment.delete()

        return Response([], status.HTTP_200_OK)

    @resaas_action(
        detail=True,
        methods=['POST'],
        permission='add_branchusergroup',
    )
    def addGroup(self, request, id):
        target, error = self._group_assignment_guard(request, id)
        if error:
            return error

        group, error = self._entity_group_or_error(request, request.data.get('group'))
        if error:
            return error

        with transaction.atomic():
            # Membership: the user must already belong to this Entity (the
            # convention UserAPIView.update() uses). Bringing a user in is a
            # separate authorization (add_entityuser), checked here rather
            # than granted silently.
            if not self._is_entity_member(request, target):
                if not isPermited(request=request, role='add_entityuser'):
                    return self._group_error(request, "user_not_in_entity", "This user is not a member of the current entity.", status.HTTP_403_FORBIDDEN)

                EntityUser.objects.get_or_create(user=target, entity_id=request.entity_id)

            branch = Branch.objects.get(id=request.branch_id, entity_id=request.entity_id)
            BranchUser.objects.get_or_create(user=target, branch=branch)

            assignment = BranchUserGroup.all_objects.filter(
                user_id=target.id,
                branch_id=branch.id,
                group_id=group.id,
            ).first()

            if assignment and not assignment.deleted_at:
                return self._group_error(request, "group_already_assigned", "This profile is already assigned to the user.", status.HTTP_409_CONFLICT)

            if assignment:
                assignment.deleted_at = None
                assignment.save(update_fields=['deleted_at'])
                message = 'Group linked successfully'
            else:
                assignment = BranchUserGroup.objects.create(user=target, group=group, branch=branch)
                message = 'Group added successfully'

        return Response(
            {
                'id': assignment.id,
                'user': str(target.id),
                'group': str(group.id),
                'branch': str(branch.id),
                'alert_success': message,
            },
            status=status.HTTP_200_OK
        )

    # ------------------------------------------------------------------
    # TEMPORARY PASSWORD (security section of the User details)
    #
    # passwordSecurity            GET   state only (no secret)        view_user
    # viewTemporaryPassword       POST  reveals it - audited          view_temporary_password
    # regenerateTemporaryPassword POST  replaces it - audited         regenerate_temporary_password
    #
    # All PROTECTED (never public): authenticated + signed tenant context +
    # permission + entity scope, enforced here; the permissions are the ones
    # created by create_model_permissions (MODULE_PERMISSIONS), granted
    # explicitly. The normal User serializer never carries any of this, and
    # revealing is a POST so it is never cached, prefetched or replayed by a
    # link.
    # ------------------------------------------------------------------

    def _secure_target(self, request, id, permission):
        """Returns (target_user, error_response). Exactly one is not None."""
        if not request.user or not request.user.is_authenticated:
            return None, self._group_error(request, "authentication_required", "Authentication required.", status.HTTP_401_UNAUTHORIZED)

        if not getattr(request, "entity_id", None) or not getattr(request, "branch_id", None):
            return None, self._group_error(request, "tenant_context_required", "RESAAS context is required.", status.HTTP_403_FORBIDDEN)

        if not isPermited(request=request, role=permission):
            return None, self._group_error(request, "permission_denied", "Permission denied", status.HTTP_403_FORBIDDEN)

        try:
            target = User.objects.filter(pk=id).first()
        except (ValueError, DjangoValidationError):
            target = None

        # tenant scope: a member of THIS entity, or an account whose
        # temporary password was issued in this entity's context. Anything
        # else is "not found" - existence is not revealed across entities.
        in_scope = target is not None and (
            EntityUser.objects.filter(entity_id=request.entity_id, user_id=target.id).exists()
            or UserTemporaryPassword.objects.filter(user_id=target.id, entity_id=request.entity_id).exists()
        )

        if not in_scope:
            return None, self._group_error(request, "user_not_found", "User not found.", status.HTTP_404_NOT_FOUND)

        return target, None

    @resaas_action(detail=True, methods=['GET'], permission='view_user')
    def passwordSecurity(self, request, id, *args, **kwargs):
        target, error = self._secure_target(request, id, 'view_user')
        if error:
            return error

        return Response(
            {**temporary_password_service.details(target), "two_factor": two_factor_service.summary_for(target, getattr(request, "entity_id", None))},
            status.HTTP_200_OK,
        )

    @resaas_action(detail=True, methods=['POST'], permission='view_temporary_password')
    def viewTemporaryPassword(self, request, id, *args, **kwargs):
        target, error = self._secure_target(request, id, 'view_temporary_password')
        if error:
            return error

        try:
            password = temporary_password_service.reveal(target, actor=request.user, request=request)
        except TemporaryPasswordError as exc:
            http_status = status.HTTP_410_GONE if exc.code == "temporary_password_expired" else status.HTTP_404_NOT_FOUND
            return self._group_error(request, exc.code, exc.message, http_status)

        response = Response(
            {"password": password, **temporary_password_service.details(target)},
            status.HTTP_200_OK,
        )
        response["Cache-Control"] = "no-store"
        return response

    @resaas_action(detail=True, methods=['POST'], permission='regenerate_temporary_password')
    def regenerateTemporaryPassword(self, request, id, *args, **kwargs):
        target, error = self._secure_target(request, id, 'regenerate_temporary_password')
        if error:
            return error

        if target.pk == request.user.pk:
            return self._group_error(request, "cannot_regenerate_own_password", "You cannot regenerate your own password.", status.HTTP_400_BAD_REQUEST)

        temporary_password_service.issue(target, actor=request.user, request=request, regenerate=True)

        return Response(temporary_password_service.details(target), status.HTTP_200_OK)
