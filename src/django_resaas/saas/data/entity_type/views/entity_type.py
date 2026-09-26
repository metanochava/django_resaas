import json

from django.http import HttpResponse
from django_resaas.saas.core.base.access import ActionPermissionMixin, ExplicitAccessMixin
import importlib
import importlib.util

from django.conf import settings as dj_settings
from django_resaas.saas.models.group import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django_resaas.saas.data.permission.serializers.permission import PermissionSerializer

from rest_framework import viewsets, filters, status
from django_resaas.saas.core.decorators.action import resaas_action
from rest_framework.response import Response
from django.db.models import F
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.core.services import entity_type_profiles_io_service, group_permissions_io_service
from django_resaas.saas.core.utils.full_path import FullPath

from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.data.branch.serializers.branch import BranchSerializer
        
from django_resaas.saas.models.app import App
from django_resaas.saas.models.entity_type_app import EntityTypeApp
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_type_model import EntityTypeModel
from django_resaas.saas.models.entity_model import EntityModel
from django_resaas.saas.models.theme import Theme
from django_resaas.saas.models.typography import Typography
from django_resaas.saas.models.layout_setting import LayoutSetting
from django_resaas.saas.models.animation_setting import AnimationSetting
from django_resaas.saas.data.theme.serializers.theme import ThemeSerializer, TypographySerializer
from django_resaas.saas.data.layout_setting.serializers.layout_setting import LayoutSettingSerializer, AnimationSettingSerializer


from django_resaas.saas.models.entity_type_group import EntityTypeGroup  # 🔥 NOVO
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.core.base.views import BaseAPIView
from django_resaas.saas.core.utils.sub_object_put import apply_sub_object_put


from django_resaas.saas.data.entity_type.serializers.entity_type import (
    EntityTypePublicSerializer,
    EntityTypeSerializer,
)
from django_resaas.saas.core.base.permissions import isPermited


class EntityTypeAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    # PUBLIC (explicit, READ only): needed by the login screen before there is a
    # session - the branding reads, and the catalogue list (header services
    # menu, EntityType of the domain) which then shows public fields only
    # (EntityTypePublicSerializer) unless the caller holds list_entitytype.
    public_actions = ('list', 'themeGet', 'layoutSettingsGet', 'typographyGet', 'animationSettingsGet')

    # EntityTypes are platform configuration. A member may READ their own
    # EntityType (the catalogue the Entity's group screens need); anything
    # else needs the entitytype permission - writes are platform level.
    # user_entitys only returns the caller's own Entities.
    membership_actions = ("user_entitys",)
    own_type_read_actions = ("retrieve", "models", "apps", "groups", "permissions", "profiles_json", "profiles_pdf")

    action_permissions = {
        "list": "list_entitytype",
        "retrieve": "view_entitytype",
        "models": "view_entitytype",
        "apps": "view_entitytype",
        "groups": "view_entitytype",
        "permissions": "view_entitytype",
        # every Entity / Branch of a type: crosses tenants
        "entitys": "view_entitytype",
        "branches_map": "view_entitytype",
        "create": "add_entitytype",
        "update": "change_entitytype",
        "partial_update": "change_entitytype",
        "destroy": "delete_entitytype",
        "addModel": "change_entitytype",
        "removeModel": "change_entitytype",
        "syncModels": "change_entitytype",
        "addApp": "change_entitytype",
        "removeApp": "change_entitytype",
        "themePut": "change_entitytype",
        "layoutSettingsPut": "change_entitytype",
        "typographyPut": "change_entitytype",
        "animationSettingsPut": "change_entitytype",
        "createGroup": "change_entitytype",
        "addGroup": "change_entitytype",
        "removeGroup": "change_entitytype",
        # export / import of the type's profiles and their permissions
        # (core/services/entity_type_profiles_io_service.py)
        "profiles_json": "view_entitytype",
        "profiles_pdf": "view_entitytype",
        "import_profiles": "change_entitytype",
    }

    def is_membership_request(self, request, action, kwargs):
        if super().is_membership_request(request, action, kwargs):
            return True
        own_type = getattr(request, "entity_type_id", None)
        return (
            action in self.own_type_read_actions
            and own_type is not None
            and str(kwargs.get(self.lookup_field)) == str(own_type)
        )

    search_fields = ['id', 'name']
    filter_backends = (filters.SearchFilter,)

    serializer_class = EntityTypeSerializer
    queryset = EntityType.all_objects.all()
    lookup_field = 'id'

    def _full_catalogue(self):
        """list_entitytype (or platform) sees every field and deleted types;
        anyone else gets the public summary of the live ones."""
        if getattr(self, "_full_catalogue_cache", None) is not None:
            return self._full_catalogue_cache
        request = self.request
        allowed = False
        if request.user and request.user.is_authenticated:
            try:
                allowed = isPermited(request=request, role="list_entitytype")
            except Exception:
                allowed = False
        self._full_catalogue_cache = allowed
        return allowed

    def get_serializer_class(self):
        if self.action == "list" and not self._full_catalogue():
            return EntityTypePublicSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        if self.action == "list" and not self._full_catalogue():
            self._paginator = None
            return EntityType.objects.filter(deleted_at__isnull=True).order_by("ordem")

        # print(self.request.query_params, self.request.query_params.get('all'), self.request.query_params.get('objects'))
        result = self.queryset.order_by('ordem')
        if self.request.query_params.get('objects')=='all':
            result = self.queryset.order_by('ordem')

        self._paginator = None
        if self.request.query_params.get('objects')=='alive':
            result = self.queryset.filter(deleted_at__isnull=True).order_by('ordem')

        if self.request.query_params.get('objects')=='deleted':
            result = self.queryset.filter(deleted_at__isnull=False).order_by('ordem')

        return result

    # ===============================
    # USER ENTIDADES
    # ===============================
    @resaas_action(detail=True, methods=['GET'])
    def user_entitys(self, request, id):
        entitys = Entity.objects.filter(entity_type__id=id)
        resultado = []

        for entity in entitys:
            try:
                EntityUser.objects.get(entity=entity, user=request.user)
                logo = FullPath.url(request, entity.logo.name, temporary=False)

                resultado.append({
                    'id': entity.id,
                    'name': entity.name,
                    'logo': logo,
                })
            except EntityUser.DoesNotExist:
                continue

        return Response(resultado, status=status.HTTP_200_OK)

    # ===============================
    # ENTIDADES
    # ===============================
    @resaas_action(detail=True, methods=['GET'])
    def entitys(self, request, id):
        entitys = Entity.objects.filter(entity_type__id=id)
        return Response(
            [{'id': e.id, 'name': e.name} for e in entitys],
            status=status.HTTP_200_OK
        )

    # ===============================
    # BRANCHES DE TODAS AS ENTIDADES DESTE TIPO (MAPA)
    # ===============================
    @resaas_action(detail=True, methods=['GET'])
    def branches_map(self, request, id):
        branches = Branch.objects.filter(
            entity__entity_type_id=id
        ).select_related('entity')

        data = BranchSerializer(
            branches, many=True, context={'request': request}
        ).data

        for branch, row in zip(branches, data):
            row['entity_name'] = branch.entity.name

        return Response(data, status=status.HTTP_200_OK)

    
    # ===============================
    # MODELOS
    # ===============================
    @resaas_action(detail=True, methods=['GET'])
    def models(self, request, id):
        entity_type = EntityType.objects.get(id=id)

        models = [
            {
                'id': tem.model.id,
                'model': tem.model.model,
                'app_label': tem.model.app_label,
            }
            for tem in EntityTypeModel.objects.filter(entity_type=entity_type)
        ]

        return Response(models, status=status.HTTP_200_OK)

    # ===============================
    # ADD MODELO
    # ===============================
    @resaas_action(detail=True, methods=['POST'])
    def addModel(self, request, id):
        entity_type = EntityType.objects.get(id=id)
        model = ContentType.objects.get(id=request.data['id'])

        EntityTypeModel.objects.get_or_create(
            entity_type=entity_type,
            model=model,
            defaults={"state": "Active"}
        )

        for entity in Entity.objects.filter(entity_type_id=id):
            EntityModel.objects.get_or_create(
                entity=entity,
                model=model,
                defaults={"state": "Active"}
            )

        return Response({
            'id': model.id,
            'model': model.model,
            'alert_success': Translate.tdc(request, f'Application <b>{model.model}</b> created successfully')
        }, status=status.HTTP_201_CREATED)

    # ===============================
    # REMOVE MODELO
    # ===============================
    @resaas_action(detail=True, methods=['POST'])
    def removeModel(self, request, id):
        entity_type = EntityType.objects.get(id=id)
        model = ContentType.objects.get(id=request.data['id'])

        EntityTypeModel.objects.filter(
            entity_type=entity_type,
            model=model
        ).delete()

        for entity in Entity.objects.filter(entity_type_id=id):
            EntityModel.objects.filter(
                entity=entity,
                model=model
            ).delete()

        return Response({
            'id': model.id,
            'model': model.model,
            'alert_success': Translate.tdc(request, f'Application <b>{model.model}</b> removed successfully')
        }, status=status.HTTP_201_CREATED)

 
    # ===============================
    # SYNC MODELOS (🔥 PRINCIPAL)
    # ===============================
    @resaas_action(detail=True, methods=['POST'])
    def syncModels(self, request, id):
        try:
            entity_type = EntityType.objects.get(id=id)
            ids = request.data.get('ids', [])

            # 🔥 validação
            if not isinstance(ids, list):
                return Response({"error": "ids must be list"}, status=400)

            # 🔥 models atuais
            atuais = set(
                EntityTypeModel.objects.filter(entity_type=entity_type)
                .values_list('model_id', flat=True)
            )

            novos = set(ids)

            para_adicionar = novos - atuais
            para_remover = atuais - novos

            # 🔥 evitar N+1
            entitys = list(Entity.objects.filter(entity_type_id=id))

            # ============================
            # ➕ ADICIONAR
            # ============================
            if para_adicionar:
                models_add = ContentType.objects.filter(id__in=para_adicionar)

                # EntityTypeModel
                EntityTypeModel.objects.bulk_create([
                    EntityTypeModel(entity_type=entity_type, model=m)
                    for m in models_add
                ], ignore_conflicts=True)

                # EntityModel
                EntityModel.objects.bulk_create([
                    EntityModel(entity=e, model=m)
                    for e in entitys
                    for m in models_add
                ], ignore_conflicts=True)

            # ============================
            # ➖ REMOVER
            # ============================
            if para_remover:
                models_remove = ContentType.objects.filter(id__in=para_remover)

                EntityTypeModel.objects.filter(
                    entity_type=entity_type,
                    model__in=models_remove
                ).delete()

                EntityModel.objects.filter(
                    entity__in=entitys,
                    model__in=models_remove
                ).delete()

            return Response({
                "success": True,
                "added": list(para_adicionar),
                "removed": list(para_remover),
                "alert_success": Translate.tdc(
                    request,
                    "Models synced successfully"
                )
            })

        except EntityType.DoesNotExist:
            return Response({
                "success": False,
                "error": "EntityType not found"
            }, status=404)

        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=400)



        



    # ===============================
    # 🔥 GET MODULOS DO TIPO
    # ===============================
    @resaas_action(detail=True, methods=['GET'])
    def apps(self, request, id):
        tipo = self.get_object()

        relacoes = EntityTypeApp.objects.filter(
            entity_type=tipo
        ).select_related('app')

        return Response([
            {
                "id": rel.app.id,
                "name": rel.app.name
            }
            for rel in relacoes
        ], status=status.HTTP_200_OK)


    # ===============================
    # 🔥 ADD MODULO
    # ===============================
    @resaas_action(detail=True, methods=['POST'])
    def addApp(self, request, id):
        tipo = self.get_object()
        app_id = request.data.get("id")

        app = App.objects.filter(id=app_id).first()
        if not app:
            return Response({"error": "App not found"}, status=400)

        EntityTypeApp.objects.get_or_create(
            entity_type=tipo,
            app=app,
            defaults={"state": "Active"}
        )

        return Response({
            "id": app.id,
            "name": app.name
        }, status=status.HTTP_201_CREATED)


    # ===============================
    # 🔥 REMOVE MODULO
    # ===============================
    @resaas_action(detail=True, methods=['POST'])
    def removeApp(self, request, id):
        tipo = self.get_object()
        app_id = request.data.get("id")

        EntityTypeApp.objects.filter(
            entity_type=tipo,
            app_id=app_id
        ).delete()

        return Response({"success": True})


    @resaas_action(detail=True, methods=['GET'])
    def themeGet(self, request, *args, **kwargs):
        entitytype = self.get_object()
        entitytype = EntityType.objects.get(id=entitytype.id )
        if entitytype.theme:
            theme = ThemeSerializer(Theme.objects.get(id=entitytype.theme.id)).data
        else:
            theme = {}
        return Response(theme, status=status.HTTP_200_OK)

    @resaas_action(detail=True, methods=['GET'])
    def layoutSettingsGet(self, request, *args, **kwargs):
        entitytype = self.get_object()
        entitytype = EntityType.objects.get(id=entitytype.id )
        if entitytype.layout_settings:
            layout_settings = LayoutSettingSerializer(LayoutSetting.objects.get(id=entitytype.layout_settings.id)).data
        else:
            layout_settings = {}
        return Response(layout_settings, status=status.HTTP_200_OK)

    
    @resaas_action(detail=True, methods=['GET'])
    def typographyGet(self, request, *args, **kwargs):
        entitytype = self.get_object()
        entitytype = EntityType.objects.get(id=entitytype.id )
        if entitytype.typography:
            typography = TypographySerializer(Typography.objects.get(id=entitytype.typography.id)).data
        else:
            typography = {}
        return Response(typography, status=status.HTTP_200_OK)

    @resaas_action(detail=True, methods=['GET'])
    def animationSettingsGet(self, request, *args, **kwargs):
        entitytype = self.get_object()
        entitytype = EntityType.objects.get(id=entitytype.id )
        if entitytype.animation_settings:
            animation_settings = AnimationSettingSerializer(AnimationSetting.objects.get(id=entitytype.animation_settings.id)).data
        else:
            animation_settings = {}
        return Response(animation_settings, status=status.HTTP_200_OK)



    @resaas_action(detail=True, methods=['PUT'])
    def themePut(self, request, *args, **kwargs):
        entitytype = self.get_object()

        theme = entitytype.theme
        data = request.data

        apply_sub_object_put(theme, data, user=request.user)

        theme.save()
        theme = ThemeSerializer(theme).data
        return Response(theme, status=status.HTTP_200_OK)


    @resaas_action(detail=True, methods=['PUT'])
    def layoutSettingsPut(self, request, *args, **kwargs):
        entitytype = self.get_object()

        layout_settings = entitytype.layout_settings
        data = request.data

        apply_sub_object_put(layout_settings, data, user=request.user)

        layout_settings.save()
        layout_settings = LayoutSettingSerializer(layout_settings).data
        return Response(layout_settings, status=status.HTTP_200_OK)




    @resaas_action(detail=True, methods=['PUT'])
    def typographyPut(self, request, *args, **kwargs):
        entitytype = self.get_object()

        typography = entitytype.typography
        data = request.data

        apply_sub_object_put(typography, data, user=request.user)
        typography.save()
        typography = TypographySerializer(typography).data
        return Response(typography, status=status.HTTP_200_OK)


    @resaas_action(detail=True, methods=['PUT'])
    def animationSettingsPut(self, request, *args, **kwargs):
        entitytype = self.get_object()

        animation_settings = entitytype.animation_settings
        data = request.data

        apply_sub_object_put(animation_settings, data, user=request.user)

        animation_settings.save()
        animation_settings = AnimationSettingSerializer(animation_settings).data
        return Response(animation_settings, status=status.HTTP_200_OK)


    # ===============================
    # 🔥 GROUPS (FINAL LIMPO)
    # ===============================


    # ===============================
    # PROFILES -> PERMISSIONS (export / import)
    # ===============================
    @resaas_action(detail=True, methods=["GET"], label="Download profiles (JSON)", icon="data_object",
                   permission="view_entitytype")
    def profiles_json(self, request, id):
        entity_type = self.get_object()
        response = HttpResponse(
            json.dumps(entity_type_profiles_io_service.export(entity_type), ensure_ascii=False, indent=2),
            content_type="application/json; charset=utf-8",
        )
        name = "".join(c if c.isalnum() or c in "-_" else "_" for c in entity_type.name)[:60] or "entity_type"
        response["Content-Disposition"] = f'attachment; filename="{name}-profiles.json"'
        return response

    @resaas_action(detail=True, methods=["GET"], label="Download profiles (PDF)", icon="picture_as_pdf",
                   permission="view_entitytype")
    def profiles_pdf(self, request, id):
        entity_type = self.get_object()
        rows = entity_type_profiles_io_service.pdf_rows(entity_type)
        return group_permissions_io_service.render_list_pdf(
            self, request,
            title=f"{Translate.tdc(request, 'Profiles')} - {entity_type.name}",
            section_title=f"{len(rows)} {Translate.tdc(request, 'permissions')}",
            fields=[("profile", "Profile"), ("app", "App"), ("model", "Model"),
                    ("codename", "Codename"), ("name", "Name")],
            rows=rows,
        )

    @resaas_action(detail=True, methods=["POST"], label="Import profiles (JSON)", icon="upload_file",
                   permission="change_entitytype")
    def import_profiles(self, request, id):
        """multipart: file=<json>, mode=add|replace (default add). All or
        nothing; profiles not in the file are untouched."""
        summary = entity_type_profiles_io_service.import_json(
            request, self.get_object(), request.FILES.get("file"), request.data.get("mode") or "add",
        )
        return Response(summary, status=status.HTTP_200_OK)

    @resaas_action(detail=True, methods=['POST'])
    def createGroup(self, request, id):
        tipo = self.get_object()

        name = request.data.get("name")
        if not name:
            return Response({"error": "name is required"}, status=400)

        group = Group.objects.create(name=name)

        # 🔥 EntityType
        EntityTypeGroup.objects.get_or_create(
            entity_type=tipo,
            group=group,
            defaults={"state": "Active"}
        )

        # 🔥 Entitys
        for entity in Entity.objects.filter(entity_type_id=id):
            EntityGroup.objects.get_or_create(
                entity=entity,
                group=group,
                defaults={"state": "Active"}
            )

        return Response({
            "id": group.id,
            "name": group.name
        })

    @resaas_action(detail=True, methods=['GET'])
    def groups(self, request, id):
        tipo = EntityType.objects.get(id=id)

        groups = EntityTypeGroup.objects.filter(
            entity_type=tipo
        ).select_related('group')

        return Response([
            {
                "id": g.group.id,
                "name": g.group.name
            }
            for g in groups
        ], status=status.HTTP_200_OK)

    @resaas_action(detail=True, methods=['POST'])
    def addGroup(self, request, id):
        tipo = EntityType.objects.get(id=id)
        group_id = request.data.get("group")

        group = Group.objects.filter(id=group_id).first()
        if not group:
            return Response({"error": "Group not found"}, status=400)

        EntityTypeGroup.objects.get_or_create(
            entity_type=tipo,
            group=group,
            defaults={"state": "Active"}
        )

        return Response({"success": True})


    @resaas_action(detail=True, methods=['POST'])
    def removeGroup(self, request, id):
        tipo = EntityType.objects.get(id=id)
        group_id = request.data.get("group")

        group = Group.objects.filter(id=group_id).first()
        if not group:
            return Response({"error": "Group not found"}, status=400)

        EntityTypeGroup.objects.filter(
            entity_type=tipo,
            group=group
        ).delete()

        return Response({"success": True})


    @resaas_action(detail=True, methods=['GET'])
    def permissions(self, request, id):
        type_id = EntityType.objects.get(id=id)
        queryset = (
            Permission.objects
            .select_related('content_type')
            .annotate(
                content_type_model=F('content_type__model'),
                content_type_app=F('content_type__app_label')
            )
        )

        if type_id:
            queryset = queryset.filter(
                content_type__in=EntityTypeModel.objects.filter(
                    entity_type_id=type_id
                ).values_list('model', flat=True)  
            )


        serializer = PermissionSerializer(queryset.order_by(
            'content_type__app_label',
            'content_type__model',
            'codename'
        ), many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)



        
