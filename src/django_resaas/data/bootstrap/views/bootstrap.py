from django.db import transaction
from django.contrib.auth.models import Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django_resaas.models.entity_type import EntityType
from django_resaas.models.entity import Entity
from django_resaas.models.branch import Branch
from django_resaas.models.entity_user import EntityUser
from django_resaas.models.branch_user import BranchUser
from django_resaas.models.branch_user_group import BranchUserGroup

from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils import all

 
 
class TenantAPIView(APIView):
    """
    Bootstrap inicial:
    EntityType → Entity → Branch → Group
    Tudo associado a um utilizador.
    """
    permission_classes = [IsAuthenticated]

    # @transaction.atomic
    def get(self, request):
        user = request.user

        data = {
            "entity_type": "Saas",
            "entity": "Entity",
            "branch": "Main",
            "group": "Admin",
        }

        # ------------------------
        # 1. EntityType
        # ------------------------
        entity_type, _ = EntityType.objects.get_or_create(
            name=data["entity_type"],
            estado = 1
        )

        # ------------------------
        # 2. Entity
        # ------------------------
        entity, created_entity = Entity.objects.get_or_create(
            name=data["entity"],
            entity_type=entity_type
        )

        # ManyToMany → DEPOIS
        entity.admins.add(user)

        EntityUser.objects.get_or_create(
            user=user,
            entity=entity,
            estado = 1
        )

        # ------------------------
        # 3. Branch
        # ------------------------
        branch, _ = Branch.objects.get_or_create(
            name=data["branch"],
            entity=entity,
            estado = 1
        )

        BranchUser.objects.get_or_create(
            user=user,
            branch=branch,
            estado = 1
        )

        # ------------------------
        # 4. Group
        # ------------------------
        group, _ = Group.objects.get_or_create(
            name=data["group"],
            estado = 1
        )

        BranchUserGroup.objects.get_or_create(
            user=user,
            branch=branch,
            group=group,
            estado = 1
        )

        user.groups.add(group)

        # ------------------------
        # RESPONSE
        # ------------------------
        return all(request, "Configuração inicial criada com sucesso", data = { "entity_type": entity_type.name, "entity": entity.name, "branch": branch.name,  "group": group.name, "user": user.username, },
            status=status.HTTP_201_CREATED
        )
