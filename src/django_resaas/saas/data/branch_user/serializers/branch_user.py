from rest_framework import serializers


from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.core.base.serializers import BaseSerializer

class BranchUserSerializer(BaseSerializer):
    class Meta:
        model = BranchUser
        fields = "__all__"

    def validate(self, attrs):
        # User carries no `entity`, so TenantRelationsMixin cannot see it:
        # only a member of the current Entity may be given access to one of
        # its branches (same rule as UserAPIView.addGroup).
        attrs = super().validate(attrs)

        request = self.context.get("request")
        entity_id = getattr(request, "entity_id", None)
        user = attrs.get("user")

        if entity_id and user is not None and not EntityUser.objects.filter(entity_id=entity_id, user_id=user.id).exists():
            raise serializers.ValidationError({"user": "This user is not a member of the current entity."})

        return attrs
