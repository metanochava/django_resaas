from rest_framework import serializers

from django_resaas.saas.core.forms.definition import FormDefinitionError, validate_definition
from django_resaas.saas.models.form_definition import FormDefinition


class FormDefinitionSerializer(serializers.ModelSerializer):
    """The layer's scope (level, entity_type, branch) is checked by the view;
    the Entity is never taken from the client. `definition` is validated as
    a form definition of the same key."""

    class Meta:
        model = FormDefinition
        fields = ["id", "key", "level", "entity_type", "entity", "branch", "version", "status",
                  "definition", "published_at", "created_at", "updated_at"]
        read_only_fields = ["entity", "version", "status", "published_at", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        key = attrs.get("key", getattr(self.instance, "key", None))
        definition = attrs.get("definition", getattr(self.instance, "definition", None))
        try:
            validate_definition(definition)
        except FormDefinitionError as error:
            raise serializers.ValidationError({"definition": [str(error)]})
        if definition.get("key") != key:
            raise serializers.ValidationError({"definition": ["Its key must be the form's key."]})
        return attrs
