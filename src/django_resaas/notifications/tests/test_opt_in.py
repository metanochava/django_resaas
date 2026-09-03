"""Spec section 87: every layer defaults to "do not send", and turning
any single layer off (while everything else stays on) must still result
in nothing being created."""

import pytest

from django_resaas.engine.core.events import EventDispatcher
from django_resaas.notifications.enums import Category, Channel
from django_resaas.notifications.models import (
    NotificationOutbox,
    NotificationPreference,
)

pytestmark = pytest.mark.django_db


def _emit(entity, branch, actor, event="sales.sale.confirmed"):
    return EventDispatcher.emit(
        event,
        entity_id=entity.id,
        branch_id=branch.id,
        actor=actor,
        context={"context_value": "x"},
    )


def test_system_disabled_creates_nothing(settings, make_rule, notification_tenant):
    settings.NOTIFICATIONS_ENABLED = False

    make_rule(recipient_config={"email": "a@example.com"})

    _emit(
        notification_tenant["entity"],
        notification_tenant["branch"],
        notification_tenant["user"],
    )

    assert NotificationOutbox.objects.count() == 0


def test_rule_disabled_creates_nothing(make_rule, notification_tenant):
    make_rule(enabled=False, recipient_config={"email": "a@example.com"})

    _emit(
        notification_tenant["entity"],
        notification_tenant["branch"],
        notification_tenant["user"],
    )

    assert NotificationOutbox.objects.count() == 0


def test_module_not_active_creates_nothing(bootstrap_tenant):
    """The rule's `module` must be an EntityApp active for this entity -
    here we deliberately don't activate "sales"."""

    from django_resaas.notifications.models import NotificationSettings

    tenant = bootstrap_tenant("no-module-user")  # no modules activated
    NotificationSettings.objects.create(entity=tenant["entity"], email_enabled=True)

    from django_resaas.notifications.models import (
        NotificationRule,
        NotificationTemplate,
    )

    rule = NotificationRule.objects.create(
        entity=tenant["entity"],
        event="sales.sale.confirmed",
        module="sales",
        channel=Channel.EMAIL,
        enabled=True,
        recipient_strategy="explicit",
        recipient_config={"email": "a@example.com"},
    )
    NotificationTemplate.objects.create(rule=rule, entity=tenant["entity"], body="hi")

    _emit(tenant["entity"], tenant["branch"], tenant["user"])

    assert NotificationOutbox.objects.count() == 0


def test_channel_disabled_creates_nothing(make_rule, notification_tenant):
    from django_resaas.notifications.models import NotificationSettings

    NotificationSettings.objects.filter(
        entity=notification_tenant["entity"], branch=None
    ).update(email_enabled=False)

    make_rule(recipient_config={"email": "a@example.com"})

    _emit(
        notification_tenant["entity"],
        notification_tenant["branch"],
        notification_tenant["user"],
    )

    assert NotificationOutbox.objects.count() == 0


def test_no_settings_row_creates_nothing(bootstrap_tenant, activate_module):
    """Provider configured (Fake, always "configured" in tests) but no
    NotificationSettings row at all = channel off (spec: absence of
    configuration means DO NOT SEND)."""

    tenant = bootstrap_tenant("no-settings-user", modules=("sales",))

    from django_resaas.notifications.models import (
        NotificationRule,
        NotificationTemplate,
    )

    rule = NotificationRule.objects.create(
        entity=tenant["entity"],
        event="sales.sale.confirmed",
        module="sales",
        channel=Channel.EMAIL,
        enabled=True,
        recipient_strategy="explicit",
        recipient_config={"email": "a@example.com"},
    )
    NotificationTemplate.objects.create(rule=rule, entity=tenant["entity"], body="hi")

    _emit(tenant["entity"], tenant["branch"], tenant["user"])

    assert NotificationOutbox.objects.count() == 0


def test_marketing_without_consent_creates_nothing(make_rule, notification_tenant):
    make_rule(category=Category.MARKETING, recipient_config={"email": "a@example.com"})

    _emit(
        notification_tenant["entity"],
        notification_tenant["branch"],
        notification_tenant["user"],
    )

    assert NotificationOutbox.objects.count() == 0


def test_marketing_with_explicit_consent_creates_outbox(make_rule, notification_tenant):
    NotificationPreference.objects.create(
        entity=notification_tenant["entity"],
        recipient_type="explicit",
        recipient_key="explicit:a@example.com",
        channel=Channel.EMAIL,
        category=Category.MARKETING,
        enabled=True,
    )

    make_rule(category=Category.MARKETING, recipient_config={"email": "a@example.com"})

    _emit(
        notification_tenant["entity"],
        notification_tenant["branch"],
        notification_tenant["user"],
    )

    assert NotificationOutbox.objects.count() == 1


def test_explicit_opt_out_creates_nothing(make_rule, notification_tenant):
    NotificationPreference.objects.create(
        entity=notification_tenant["entity"],
        recipient_type="explicit",
        recipient_key="explicit:a@example.com",
        channel=Channel.EMAIL,
        category=Category.TRANSACTIONAL,
        enabled=False,
    )

    make_rule(recipient_config={"email": "a@example.com"})

    _emit(
        notification_tenant["entity"],
        notification_tenant["branch"],
        notification_tenant["user"],
    )

    assert NotificationOutbox.objects.count() == 0


def test_fully_configured_creates_one_outbox(make_rule, notification_tenant):
    make_rule(recipient_config={"email": "a@example.com"})

    _emit(
        notification_tenant["entity"],
        notification_tenant["branch"],
        notification_tenant["user"],
    )

    assert NotificationOutbox.objects.count() == 1
