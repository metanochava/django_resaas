import re

from rest_framework import serializers

from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.theme import Theme
from django_resaas.saas.models.typography import Typography

# a plain CSS colour: #hex, rgb()/rgba(), hsl()/hsla() - the values end up in
# CSS variables and e-mail style attributes
CSS_COLOR = re.compile(r"^(#[0-9a-fA-F]{3,8}|(rgb|rgba|hsl|hsla)\([0-9.,%\s]+\))$")


class ThemeSerializer(BaseSerializer):
    permanent_fields_files = []
    # where the theme belongs: "template" (no owner, shared), "entity_type",
    # "entity" or "user" (a customized copy - ThemeAPIView.customize)
    owner_scope = serializers.SerializerMethodField()

    class Meta:
        model = Theme
        fields = "__all__"
        # ownership is set by ThemeAPIView.customize only, never by the client
        read_only_fields = ["owner_entity_type", "owner_entity", "owner_user"]

    def get_owner_scope(self, obj):
        if obj.owner_user_id:
            return "user"
        if obj.owner_entity_id:
            return "entity"
        if obj.owner_entity_type_id:
            return "entity_type"
        return "template"


class ThemeCustomizeSerializer(serializers.Serializer):
    """POST themes/{id}/customize/: copy a theme for one level and apply it.

    scope   "user" (the caller), "entity" (the Entity of the signed context) or
            "entity_type" (`target`, an EntityType id)
    name    name of the copy (default: "<source> (<level name>)")
    values  colours to change on the copy, {field: "#rrggbb"}; only the
            CUSTOMIZABLE_FIELDS, only plain CSS colours
    """

    CUSTOMIZABLE_FIELDS = (
        "primary", "secondary", "accent", "positive", "negative", "warning", "info",
        "background", "page", "card", "header", "header_text", "footer", "footer_text",
        "text_primary", "text_secondary", "text_link", "sidebar", "sidebar_text", "sidebar_active",
        "button_primary", "button_primary_text", "button_secondary", "button_secondary_text",
    )

    scope = serializers.ChoiceField(choices=("user", "entity", "entity_type"))
    target = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    values = serializers.DictField(child=serializers.CharField(max_length=50), required=False, default=dict)

    def validate_values(self, values):
        unknown = sorted(set(values) - set(self.CUSTOMIZABLE_FIELDS))
        if unknown:
            raise serializers.ValidationError(f"Not customizable: {', '.join(unknown)}")
        bad = sorted(key for key, value in values.items() if not CSS_COLOR.match(str(value).strip()))
        if bad:
            raise serializers.ValidationError(f"Not a colour: {', '.join(bad)}")
        return {key: str(value).strip() for key, value in values.items()}

class TypographySerializer(BaseSerializer):
    permanent_fields_files = []
    class Meta:
        model = Typography
        fields = "__all__"
