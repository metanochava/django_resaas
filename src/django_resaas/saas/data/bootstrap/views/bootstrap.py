from django.db import transaction
from django_resaas.saas.models.group import Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.branch_user_group import BranchUserGroup

from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.core.utils import all

 
 
class TenantAPIView(APIView):
    """
    Bootstrap inicial:
    EntityType → Entity → Branch → Group
    Tudo associado a um utilizador.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        # POST, not GET: this view creates records (a GET never changes state).
        user = request.user

        data = {
            "entity_type": "SaaS",
            "entity": "Tenant",
            "branch": "Main",
            "group": "Admin",
        }

        # ------------------------
        # 1. EntityType
        # ------------------------
        entity_type, _ = EntityType.objects.get_or_create(
            name=data["entity_type"],
            defaults={"state": "Active"},
        )

        # ------------------------
        # 2. Entity: same rule as create_root - the oldest Entity of the
        # SaaS type; only a new installation, which has none, creates it.
        # ------------------------
        entity = Entity.objects.filter(
            entity_type=entity_type
        ).order_by("created_at", "id").first()
        if entity is None:
            entity = Entity.objects.create(
                name=data["entity"],
                entity_type=entity_type,
                state="Active",
            )

        # ManyToMany → DEPOIS
        entity.admins.add(user)

        EntityUser.objects.get_or_create(
            user=user,
            entity=entity,
            defaults={"state": "Active"},
        )

        # ------------------------
        # 3. Branch
        # ------------------------
        branch, _ = Branch.objects.get_or_create(
            name=data["branch"],
            entity=entity,
            defaults={"state": "Active"},
        )

        BranchUser.objects.get_or_create(
            user=user,
            branch=branch,
            defaults={"state": "Active"},
        )

        # ------------------------
        # 4. Group
        # ------------------------
        group, _ = Group.objects.get_or_create(name=data["group"])

        BranchUserGroup.objects.get_or_create(
            user=user,
            branch=branch,
            group=group,
            defaults={"state": "Active"},
        )

        # user.groups.add(group)

        # ------------------------
        # RESPONSE
        # ------------------------
        return all(
            request,
            status=status.HTTP_201_CREATED,
            data={
                "entity_type": entity_type.name,
                "entity": entity.name,
                "branch": branch.name,
                "group": group.name,
                "user": user.username,
            },
        )
