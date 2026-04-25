from django_resaas.core.base.views import BaseAPIView, register_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

from django_resaas.core.services.bootstrap_service import BootstrapService
from django_resaas.core.services.idioma_service import IdiomaService
from django_resaas.core.services.frontend_service import FrontEndService
from django_resaas.core.services.traducao_service import TraducaoService

User = get_user_model()


@register_view('bootstraps')
class BootstrapAPIView(BaseAPIView):

    def post(self, request):
        data = request.data

        # =========================
        # 🧾 DADOS
        # =========================
        tipo_entidade = data.get('tipo_entidade')
        entidade_nome = data.get('entidade')
        sucursal_nome = data.get('sucursal')
        group_nome = data.get('group', 'Admin')
        user_id = data.get('user_id')

        # =========================
        # 🔐 VALIDAÇÃO
        # =========================
        if not all([tipo_entidade, entidade_nome, sucursal_nome, user_id]):
            return Response(
                {"error": "Campos obrigatórios: tipo_entidade, entidade, sucursal, user_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # =========================
        # 👤 VALIDAR USER
        # =========================
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        # =========================
        # 🔒 PROTEÇÃO (1x apenas)
        # =========================
        from django_resaas.models.entidade import Entidade

        if Entidade.objects.exists():
            return Response(
                {"error": "Sistema já inicializado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # =========================
            # 🚀 BOOTSTRAP
            # =========================
            result = BootstrapService.run(
                tipo_entidade,
                entidade_nome,
                sucursal_nome,
                user,
                group_nome
            )

            # =========================
            # 🌍 DEFAULT DATA
            # =========================
            IdiomaService.load_defaults()
            FrontEndService.load_defaults()
            TraducaoService.load_defaults()

            return Response({
                "message": "Sistema pronto 🚀",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username
                },
                "data": {
                    "tipo_entidade": result["tipo_entidade"].nome,
                    "entidade": result["entidade"].nome,
                    "sucursal": result["sucursal"].nome,
                    "group": result["group"].name
                }
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )