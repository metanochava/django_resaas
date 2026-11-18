from django.apps import apps
from django.contrib.auth.models import Permission
from rest_framework import serializers

from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.mobile_tab import EntityMobileTab, EntityTypeMobileTab


class _MobileTabSerializer(BaseSerializer):
    """The app must be installed and the permission must exist: a tab that
    names neither would never show (or would show the wrong thing)."""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        app = attrs.get("app", getattr(self.instance, "app", None))
        if app and app not in {config.label for config in apps.get_app_configs()}:
            raise serializers.ValidationError({"app": ["Unknown app."]})
        permission = attrs.get("permission", getattr(self.instance, "permission", None))
        if permission and not Permission.objects.filter(codename=permission).exists():
            raise serializers.ValidationError({"permission": ["Unknown permission."]})
        return attrs


class EntityTypeMobileTabSerializer(_MobileTabSerializer):
    class Meta:
        model = EntityTypeMobileTab
        fields = "__all__"


class EntityMobileTabSerializer(_MobileTabSerializer):
    # the entity is the request's (BaseAPIView.perform_create)
    class Meta:
        model = EntityMobileTab
        fields = "__all__"
        read_only_fields = ["entity"]
