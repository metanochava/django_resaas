from django.conf import settings
from django.core import signing
from rest_framework.exceptions import PermissionDenied, ValidationError

from django_resaas.models.entity import Entity
from django_resaas.models.entity_user import EntityUser
from django_resaas.models.branch import Branch
from django_resaas.models.branch_user import BranchUser
from django_resaas.models.branch_user_group import BranchUserGroup


class ResaasContextService:
    SALT = "django_resaas.tenant.context.v1"
    VERSION = 1

    @classmethod
    def get_ttl(cls):
        return getattr(settings, "RESAAS_CONTEXT_TTL", 60 * 60)

    @classmethod
    def validate_entity(cls, user, entity_id):
        if not entity_id:
            raise ValidationError({"entity_id": "Entity is required."})

        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            raise ValidationError({"entity_id": "Entity does not exist."})

        if (
            user.is_superuser
            or entity.admins.filter(id=user.id).exists()
            or EntityUser.objects.filter(entity=entity, user=user).exists()
        ):
            return entity

        raise PermissionDenied("You do not have access to this entity.")

    @classmethod
    def validate_branch(cls, user, entity, branch_id):
        if not branch_id:
            return None

        try:
            branch = Branch.objects.get(id=branch_id, entity=entity)
        except Branch.DoesNotExist:
            raise PermissionDenied("Invalid branch for this entity.")

        if (
            user.is_superuser
            or entity.admins.filter(id=user.id).exists()
            or BranchUser.objects.filter(branch=branch, user=user).exists()
        ):
            return branch

        raise PermissionDenied("You do not have access to this branch.")

    @classmethod
    def validate_group(cls, user, branch, group_id):
        if not group_id:
            return None

        if not branch:
            raise ValidationError({"group_id": "A group requires a branch."})

        if user.is_superuser or BranchUserGroup.objects.filter(
            branch=branch, user=user, group_id=group_id
        ).exists():
            return group_id

        raise PermissionDenied("You do not have access to this group.")

    @classmethod
    def build_payload(cls, user, entity, branch=None, group_id=None):
        return {
            "version": cls.VERSION,
            "user_id": str(user.id),
            "entity_type_id": str(entity.entity_type_id),
            "entity_id": str(entity.id),
            "branch_id": str(branch.id) if branch else None,
            "group_id": str(group_id) if group_id else None,
        }

    @classmethod
    def issue(cls, user, entity_id, branch_id=None, group_id=None):
        entity = cls.validate_entity(user, entity_id)
        branch = cls.validate_branch(user, entity, branch_id)
        group_id = cls.validate_group(user, branch, group_id)
        payload = cls.build_payload(user, entity, branch, group_id)

        token = signing.dumps(
            payload,
            key=settings.SECRET_KEY,
            salt=cls.SALT,
            compress=True,
        )

        return {"token": token, "context": payload}

    @classmethod
    def decode(cls, token):
        if not token:
            return None

        try:
            payload = signing.loads(
                token,
                key=settings.SECRET_KEY,
                salt=cls.SALT,
                max_age=cls.get_ttl(),
            )
        except signing.SignatureExpired:
            raise PermissionDenied("RESAAS context has expired.")
        except signing.BadSignature:
            raise PermissionDenied("Invalid RESAAS context.")

        if payload.get("version") != cls.VERSION:
            raise PermissionDenied("Unsupported RESAAS context version.")

        return payload

    @classmethod
    def validate_for_user(cls, user, payload):
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        if not payload:
            raise PermissionDenied("RESAAS context is required.")

        if str(payload.get("user_id")) != str(user.id):
            raise PermissionDenied(
                "RESAAS context does not belong to this user."
            )

        entity = cls.validate_entity(user, payload.get("entity_id"))
        branch = cls.validate_branch(user, entity, payload.get("branch_id"))
        cls.validate_group(user, branch, payload.get("group_id"))

        if str(entity.entity_type_id) != str(payload.get("entity_type_id")):
            raise PermissionDenied("Invalid entity type context.")

        return True