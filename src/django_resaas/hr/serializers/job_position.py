from rest_framework import serializers
from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.job_position import JobPosition
from django_resaas.hr.models.department import Department


class JobPositionSerializer(BaseSerializer):

    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        required=False,
        allow_null=True
    )

    department_data = serializers.SerializerMethodField()

    def get_department_data(self, obj):

        if not obj.department:
            return None

        return {
            "id": obj.department.id,
            "label": obj.department.label,
            "name": getattr(obj.department, "name", None),
        }

    class Meta:
        model = JobPosition
        fields = "__all__"

    def validate(self, attrs):
        attrs = super().validate(attrs)

        request = self.context.get("request")
        entity_id = getattr(request, "entity_id", None) if request else None
        department = attrs.get("department")

        if entity_id and department is not None and str(department.entity_id) != str(entity_id):
            raise serializers.ValidationError({
                "department": "Does not belong to the current entity."
            })

        return attrs