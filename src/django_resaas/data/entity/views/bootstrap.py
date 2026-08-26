from django_resaas.core.base.views import BaseAPIView, register_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

from django_resaas.core.services.bootstrap_service import BootstrapService
from django_resaas.core.services.language_service import LanguageService
from django_resaas.core.services.frontend_service import FrontEndService
from django_resaas.core.services.translation_service import TranslationService

User = get_user_model()


@register_view('bootstraps')
class BootstrapAPIView(BaseAPIView):

    def post(self, request):
        data = request.data

        # =========================
        # 🧾 DADOS
        # =========================
        entity_type = data.get('entity_type')
        entity_name = data.get('entity')
        branch_name = data.get('branch')
        group_name = data.get('group', 'Admin')
        user_id = data.get('user_id')

        # =========================
        # 🔐 VALIDAÇÃO
        # =========================
        if not all([entity_type, entity_name, branch_name, user_id]):
            return Response(
                {"error": "Required fields: entity_type, entity, branch, user_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # =========================
        # 👤 VALIDAR USER
        # =========================
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # =========================
        # 🔒 PROTEÇÃO (1x apenas)
        # =========================
        from django_resaas.models.entity import Entity

        if Entity.objects.exists():
            return Response(
                {"error": "System already initialized"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # =========================
            # 🚀 BOOTSTRAP
            # =========================
            result = BootstrapService.run(
                entity_type,
                entity_name,
                branch_name,
                user,
                group_name
            )

            # =========================
            # 🌍 DEFAULT DATA
            # =========================
            LanguageService.load_defaults()
            FrontEndService.load_defaults()
            TranslationService.load_defaults()

            return Response({
                "message": "System ready 🚀",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username
                },
                "data": {
                    "entity_type": result["entity_type"].name,
                    "entity": result["entity"].name,
                    "branch": result["branch"].name,
                    "group": result["group"].name
                }
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )