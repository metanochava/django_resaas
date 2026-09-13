from rest_framework import serializers

from django_resaas.saas.core.base.serializers import BaseSerializer

from .models import (
    NotificationDeliveryAttempt,
    NotificationOutbox,
    NotificationPreference,
    NotificationProviderCredential,
    NotificationRule,
    NotificationSettings,
    NotificationTemplate,
)


class NotificationRuleSerializer(BaseSerializer):
    class Meta:
        model = NotificationRule
        fields = "__all__"


class NotificationTemplateSerializer(BaseSerializer):
    class Meta:
        model = NotificationTemplate
        fields = "__all__"


class NotificationPreferenceSerializer(BaseSerializer):
    class Meta:
        model = NotificationPreference
        fields = "__all__"


class NotificationSettingsSerializer(BaseSerializer):
    class Meta:
        model = NotificationSettings
        fields = "__all__"


class NotificationOutboxSerializer(BaseSerializer):
    """List/retrieve only (the view blocks create/update/destroy) - every
    field here is effectively read-only in practice, this Meta is
    defense-in-depth, not the only thing enforcing it."""

    class Meta:
        model = NotificationOutbox
        fields = "__all__"
        read_only_fields = [f.name for f in NotificationOutbox._meta.fields]


class NotificationDeliveryAttemptSerializer(BaseSerializer):
    class Meta:
        model = NotificationDeliveryAttempt
        fields = "__all__"
        read_only_fields = [f.name for f in NotificationDeliveryAttempt._meta.fields]


class NotificationProviderCredentialSerializer(BaseSerializer):
    """`config` is the plaintext credential dict on the way in
    (write-only - never echoed back, not even on the same response) and
    is never derivable from any other field this serializer exposes -
    `encrypted_config` (the actual DB column) is deliberately excluded
    from `fields` entirely, not just marked read-only, so it can never
    leak through list/retrieve either."""

    config = serializers.JSONField(write_only=True, required=True)

    class Meta:
        model = NotificationProviderCredential
        fields = [
            "id", "entity", "branch", "channel", "provider_name",
            "is_active", "config", "created_at", "updated_at",
        ]

    def create(self, validated_data):
        config = validated_data.pop("config")
        instance = NotificationProviderCredential(**validated_data)
        instance.set_config(config)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        config = validated_data.pop("config", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if config is not None:
            instance.set_config(config)
        instance.save()
        return instance
