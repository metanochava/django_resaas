import importlib
import importlib.util

from django.apps import apps
from django.conf import settings as dj_settings
from django_resaas.models.group import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django_resaas.data.permission.serializers.permission import PermissionSerializer

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F
from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils.full_path import FullPath

from django_resaas.models.entity_type import EntityType
from django_resaas.models.entity import Entity
from django_resaas.models.entity_user import EntityUser
        
from django_resaas.models.app import App
from django_resaas.models.entity_type_app import EntityTypeApp
from django_resaas.models.branch_user_group import BranchUserGroup
from django_resaas.models.entity_type_model import EntityTypeModel
from django_resaas.models.entity_model import EntityModel
from django_resaas.models.theme import Theme, Typography
from django_resaas.models.layout_setting import LayoutSetting, AnimationSetting
from django_resaas.data.theme.serializers.theme import ThemeSerializer, TypographySerializer
from django_resaas.data.layout_setting.serializers.layout_setting import LayoutSettingSerializer, AnimationSettingSerializer


from django_resaas.models.entity_type_group import EntityTypeGroup  # 🔥 NOVO
from django_resaas.models.entity_group import EntityGroup


from django_resaas.data.entity_type.serializers.entity_type import (
    EntityTypeSerializer
)


class EntityTypeAPIView(viewsets.ModelViewSet):
    search_fields = ['id', 'name']
    filter_backends = (filters.SearchFilter,)

    serializer_class = EntityTypeSerializer
    queryset = EntityType.objects.all()
    lookup_field = 'id'


    def get_queryset(self):
        if self.request.query_params.get('all'):
            return self.queryset.order_by('ordem')

        self._paginator = None
        return self.queryset.filter(state=1).order_by('ordem')

    # ===============================
    # USER ENTIDADES
    # ===============================
    @action(detail=True, methods=['GET'])
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
    @action(detail=True, methods=['GET'])
    def entitys(self, request, id):
        entitys = Entity.objects.filter(entity_type__id=id)
        return Response(
            [{'id': e.id, 'name': e.name} for e in entitys],
            status=status.HTTP_200_OK
        )

    
    # ===============================
    # APPS
    # ===============================
    @action(detail=True, methods=['GET'])
    def apps(self, request, id):
        resultado = []

        for app in apps.get_app_configs():
            resultado.append({
                'name': app.name,
                'label': app.label,
                'verbose': app.verbose_name,
            })

        return Response(resultado, status=status.HTTP_200_OK)

    # ===============================
    # MODELOS
    # ===============================
    @action(detail=True, methods=['GET'])
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
    @action(detail=True, methods=['POST'])
    def addModel(self, request, id):
        entity_type = EntityType.objects.get(id=id)
        model = ContentType.objects.get(id=request.data['id'])

        EntityTypeModel.objects.get_or_create(
            entity_type=entity_type,
            model=model,
            state=1
        )

        for entity in Entity.objects.filter(entity_type_id=id):
            EntityModel.objects.get_or_create(
                entity=entity,
                model=model,
                state=1
            )

        return Response({
            'id': model.id,
            'model': model.model,
            'alert_success': Translate.tdc(request, f'Aplicação <b>{model.model}</b> criada com sucesso')
        }, status=status.HTTP_201_CREATED)

    # ===============================
    # REMOVE MODELO
    # ===============================
    @action(detail=True, methods=['POST'])
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
            'alert_success': Translate.tdc(request, f'Aplicação <b>{model.model}</b> removida com sucesso')
        }, status=status.HTTP_201_CREATED)

 
    # ===============================
    # SYNC MODELOS (🔥 PRINCIPAL)
    # ===============================
    @action(detail=True, methods=['POST'])
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
                    "Models sincronizados com sucesso"
                )
            })

        except EntityType.DoesNotExist:
            return Response({
                "success": False,
                "error": "EntityType não encontrado"
            }, status=404)

        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=400)



        



    # ===============================
    # 🔥 GET MODULOS DO TIPO
    # ===============================
    @action(detail=True, methods=['GET'])
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
    @action(detail=True, methods=['POST'])
    def addApp(self, request, id):
        tipo = self.get_object()
        app_id = request.data.get("id")

        app = App.objects.filter(id=app_id).first()
        if not app:
            return Response({"error": "App not found"}, status=400)

        EntityTypeApp.objects.get_or_create(
            entity_type=tipo,
            app=app
        )

        return Response({
            "id": app.id,
            "name": app.name
        }, status=status.HTTP_201_CREATED)


    # ===============================
    # 🔥 REMOVE MODULO
    # ===============================
    @action(detail=True, methods=['POST'])
    def removeApp(self, request, id):
        tipo = self.get_object()
        app_id = request.data.get("id")

        EntityTypeApp.objects.filter(
            entity_type=tipo,
            app_id=app_id
        ).delete()

        return Response({"success": True})


    @action(detail=True, methods=['GET'])
    def themeGet(self, request, *args, **kwargs):
        entitytype = self.get_object()
        entitytype = EntityType.objects.get(id=entitytype.id )
        if entitytype.theme:
            theme = ThemeSerializer(Theme.objects.get(id=entitytype.theme.id)).data
        else:
            theme = {}
        return Response(theme, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def layoutSettingsGet(self, request, *args, **kwargs):
        entitytype = self.get_object()
        entitytype = EntityType.objects.get(id=entitytype.id )
        if entitytype.layout_settings:
            layout_settings = LayoutSettingSerializer(LayoutSetting.objects.get(id=entitytype.layout_settings.id)).data
        else:
            layout_settings = {}
        return Response(layout_settings, status=status.HTTP_200_OK)

    
    @action(detail=True, methods=['GET'])
    def typographyGet(self, request, *args, **kwargs):
        entitytype = self.get_object()
        entitytype = EntityType.objects.get(id=entitytype.id )
        if entitytype.typography:
            typography = TypographySerializer(Typography.objects.get(id=entitytype.typography.id)).data
        else:
            typography = {}
        return Response(typography, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def animationSettingsGet(self, request, *args, **kwargs):
        entitytype = self.get_object()
        entitytype = EntityType.objects.get(id=entitytype.id )
        if entitytype.animation_settings:
            animation_settings = AnimationSettingSerializer(AnimationSetting.objects.get(id=entitytype.animation_settings.id)).data
        else:
            animation_settings = {}
        return Response(animation_settings, status=status.HTTP_200_OK)



    @action(detail=True, methods=['PUT'])
    def themePut(self, request, *args, **kwargs):
        entitytype = self.get_object()

        theme = entitytype.theme
        data = request.data

        for key, value in data.items():
            if hasattr(theme, key):
                if key == "created_by" or key == "updated_by":
                    theme.created_by = request.user
                    theme.updated_by = request.user
                else:
                    setattr(theme, key, value)

        theme.save()
        theme = ThemeSerializer(theme).data
        return Response(theme, status=status.HTTP_200_OK)


    @action(detail=True, methods=['PUT'])
    def layoutSettingsPut(self, request, *args, **kwargs):
        entitytype = self.get_object()

        layout_settings = entitytype.layout_settings
        data = request.data

        for key, value in data.items():
            if hasattr(layout_settings, key):
                if key == "created_by" or key == "updated_by":
                    layout_settings.created_by = request.user
                    layout_settings.updated_by = request.user
                else:
                    setattr(layout_settings, key, value)

        layout_settings.save()
        layout_settings = LayoutSettingSerializer(layout_settings).data
        return Response(layout_settings, status=status.HTTP_200_OK)




    @action(detail=True, methods=['PUT'])
    def typographyPut(self, request, *args, **kwargs):
        entitytype = self.get_object()

        typography = entitytype.typography
        data = request.data

        for key, value in data.items():
            if hasattr(typography, key):
                if key == "created_by" or key == "updated_by":
                    typography.created_by = request.user
                    typography.updated_by = request.user
                else:
                    setattr(typography, key, value)
        typography.save()
        typography = TypographySerializer(typography).data
        return Response(typography, status=status.HTTP_200_OK)


    @action(detail=True, methods=['PUT'])
    def animationSettingsPut(self, request, *args, **kwargs):
        entitytype = self.get_object()

        animation_settings = entitytype.animation_settings
        data = request.data

        for key, value in data.items():
            if hasattr(animation_settings, key):
                setattr(animation_settings, key, value)
                if key == "created_by" or key == "updated_by":
                    animation_settings.created_by = request.user
                    animation_settings.updated_by = request.user
                else:
                    setattr(animation_settings, key, value)
        

        animation_settings.save()
        animation_settings = AnimationSettingSerializer(animation_settings).data
        return Response(animation_settings, status=status.HTTP_200_OK)


    # ===============================
    # 🔥 GROUPS (FINAL LIMPO)
    # ===============================


    @action(detail=True, methods=['POST'])
    def createGroup(self, request, id):
        tipo = self.get_object()

        name = request.data.get("name")
        if not name:
            return Response({"error": "name é obrigatório"}, status=400)

        group = Group.objects.create(name=name)

        # 🔥 EntityType
        EntityTypeGroup.objects.get_or_create(
            entity_type=tipo,
            group=group
        )

        # 🔥 Entitys
        for entity in Entity.objects.filter(entity_type_id=id):
            EntityGroup.objects.get_or_create(
                entity=entity,
                group=group
            )

        return Response({
            "id": group.id,
            "name": group.name
        })

    @action(detail=True, methods=['GET'])
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

    @action(detail=True, methods=['POST'])
    def addGroup(self, request, id):
        tipo = EntityType.objects.get(id=id)
        group_id = request.data.get("group")

        group = Group.objects.filter(id=group_id).first()
        if not group:
            return Response({"error": "Group not found"}, status=400)

        EntityTypeGroup.objects.get_or_create(
            entity_type=tipo,
            group=group
        )

        return Response({"success": True})


    @action(detail=True, methods=['POST'])
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


    @action(detail=True, methods=['GET'])
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



        
