from django.contrib import admin

from .models import (
    NotificationDeliveryAttempt,
    NotificationOutbox,
    NotificationPreference,
    NotificationRule,
    NotificationSettings,
    NotificationTemplate,
)


@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "channel",
        "category",
        "priority",
        "enabled",
        "entity",
        "branch",
    )
    list_filter = ("channel", "category", "enabled", "entity")
    search_fields = ("event", "module")


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("rule", "language", "enabled")
    list_filter = ("enabled", "language")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("recipient_key", "channel", "category", "enabled", "entity")
    list_filter = ("channel", "category", "enabled")
    search_fields = ("recipient_key",)


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "entity",
        "branch",
        "email_enabled",
        "sms_enabled",
        "whatsapp_enabled",
    )
    list_filter = ("email_enabled", "sms_enabled", "whatsapp_enabled")


class ReadOnlyAdmin(admin.ModelAdmin):
    """Outbox/DeliveryAttempt are audit trails, not editable records -
    visible in the admin for triage, never editable by hand."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationOutbox)
class NotificationOutboxAdmin(ReadOnlyAdmin):
    list_display = (
        "event",
        "channel",
        "status",
        "priority",
        "entity",
        "attempts",
        "created_at",
    )
    list_filter = ("status", "channel", "category", "entity")
    search_fields = ("event", "recipient_identity", "idempotency_key")
    date_hierarchy = "created_at"


@admin.register(NotificationDeliveryAttempt)
class NotificationDeliveryAttemptAdmin(ReadOnlyAdmin):
    list_display = ("outbox", "attempt_number", "success", "provider", "started_at")
    list_filter = ("success", "provider")
    date_hierarchy = "started_at"
