from django_resaas.engine.core.base.serializers import BaseSerializer

from .models import (
    NotificationDeliveryAttempt,
    NotificationOutbox,
    NotificationPreference,
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
