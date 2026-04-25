from django.db import transaction
from django.contrib.auth.models import Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django_resaas.models.tipo_entidade import TipoEntidade
from django_resaas.models.entidade import Entidade
from django_resaas.models.sucursal import Sucursal
from django_resaas.models.entidade_user import EntidadeUser
from django_resaas.models.sucursal_user import SucursalUser
from django_resaas.models.sucursal_user_group import SucursalUserGroup

from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils import all

 
 
class TenantAPIView(APIView):
    """
    Bootstrap inicial:
    TipoEntidade → Entidade → Sucursal → Group
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
            "group": "Admin",
        }

        # ------------------------
        # 1. TipoEntidade
        # ------------------------
        tipo_entidade, _ = TipoEntidade.objects.get_or_create(
            nome=data["tipo_entidade"],
            estado = 1
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
            entidade=entidade,
            estado = 1
        )

        # ------------------------
        # 3. Sucursal
        # ------------------------
        sucursal, _ = Sucursal.objects.get_or_create(
            nome=data["sucursal"],
            entidade=entidade,
            estado = 1
        )

        SucursalUser.objects.get_or_create(
            user=user,
            sucursal=sucursal,
            estado = 1
        )

        # ------------------------
        # 4. Group
        # ------------------------
        group, _ = Group.objects.get_or_create(
            name=data["group"],
            estado = 1
        )

        SucursalUserGroup.objects.get_or_create(
            user=user,
            sucursal=sucursal,
            group=group,
            estado = 1
        )

        user.groups.add(group)

        # ------------------------
        # RESPONSE
        # ------------------------
        return all(request, "Configuração inicial criada com sucesso", data = { "tipo_entidade": tipo_entidade.nome, "entidade": entidade.nome, "sucursal": sucursal.nome,  "group": group.name, "user": user.username, },
            status=status.HTTP_201_CREATED
        )
