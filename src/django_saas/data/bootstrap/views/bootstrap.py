from django.db import transaction
from django.contrib.auth.models import Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django_saas.models.tipo_entidade import TipoEntidade
from django_saas.models.entidade import Entidade
from django_saas.models.sucursal import Sucursal
from django_saas.models.entidade_user import EntidadeUser
from django_saas.models.sucursal_user import SucursalUser
from django_saas.models.sucursal_user_group import SucursalUserGroup

from django_saas.core.utils.translate import Translate


class TenantAPIView(APIView):
    """
    Bootstrap inicial:
    TipoEntidade → Entidade → Sucursal → Grupo
    Tudo associado a um utilizador.
    """
    permission_classes = [IsAuthenticated]

    # @transaction.atomic
    def get(self, request):
        user = request.user

        data = {
            "tipo_entidade": "Saas",
            "entidade": "Mytech",
            "sucursal": "Sede",
            "grupo": "Admin",
        }

        # ------------------------
        # 1. TipoEntidade
        # ------------------------
        tipo_entidade, _ = TipoEntidade.objects.get_or_create(
            nome=data["tipo_entidade"],
            defaults={"estado": 1}
        )

        # ------------------------
        # 2. Entidade
        # ------------------------
        entidade, created_entidade = Entidade.objects.get_or_create(
            nome=data["entidade"],
            tipo_entidade=tipo_entidade
        )

        # ManyToMany → DEPOIS
        entidade.admins.add(user)

        EntidadeUser.objects.get_or_create(
            user=user,
            entidade=entidade
        )

        # ------------------------
        # 3. Sucursal
        # ------------------------
        sucursal, _ = Sucursal.objects.get_or_create(
            nome=data["sucursal"],
            entidade=entidade
        )

        SucursalUser.objects.get_or_create(
            user=user,
            sucursal=sucursal
        )

        # ------------------------
        # 4. Grupo
        # ------------------------
        grupo, _ = Group.objects.get_or_create(
            name=data["grupo"]
        )

        SucursalUserGroup.objects.get_or_create(
            user=user,
            sucursal=sucursal,
            group=grupo
        )

        user.groups.add(grupo)

        # ------------------------
        # RESPONSE
        # ------------------------
        return Response(
            {
                "alert_success": Translate.tdc(
                    request,
                    "Configuração inicial criada com sucesso"
                ),
                "data": {
                    "tipo_entidade": tipo_entidade.nome,
                    "entidade": entidade.nome,
                    "sucursal": sucursal.nome,
                    "grupo": grupo.name,
                    "user": user.username,
                }
            },
            status=status.HTTP_201_CREATED
        )
