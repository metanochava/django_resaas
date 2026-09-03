"""Spec sections 11, 42, 101-103: template snapshot survives a later
template edit, invalid recipient identity is a permanent failure with
no provider call, and the recipient resolver registry is extensible."""

import pytest

from django_resaas.engine.core.events import EventDispatcher
from django_resaas.notifications.enums import ErrorType, OutboxStatus
from django_resaas.notifications.models import NotificationOutbox
from django_resaas.notifications.recipients import Recipient, RecipientResolverRegistry
from django_resaas.notifications.tasks import process_notification

pytestmark = pytest.mark.django_db


def _emit(tenant):
    EventDispatcher.emit(
        "sales.sale.confirmed",
        entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id,
        actor=tenant["user"],
        context={"context_value": "hello"},
    )


def test_template_is_rendered_once_and_snapshotted(make_rule, notification_tenant):
    rule = make_rule(
        recipient_config={"email": "a@example.com"}, body="Value: {{ context_value }}"
    )

    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    assert outbox.body == "Value: hello"

    # Edit the template AFTER the outbox exists.
    template = rule.templates.get()
    template.body = "CHANGED {{ context_value }}"
    template.save()

    outbox.refresh_from_db()
    assert outbox.body == "Value: hello"  # snapshot untouched by the later edit


def test_invalid_email_is_permanent_failure_no_provider_call(
    make_rule, notification_tenant, fake_providers
):
    make_rule(recipient_config={"email": "not-an-email"})

    _emit(notification_tenant)
    outbox = NotificationOutbox.objects.get()

    process_notification(str(outbox.id))

    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.FAILED
    assert fake_providers["email"].sent == []  # provider never called


def test_invalid_phone_is_permanent_failure(
    make_rule, notification_tenant, fake_providers
):
    from django_resaas.notifications.enums import Channel

    make_rule(channel=Channel.SMS, recipient_config={"phone": "12345"})  # not E.164

    _emit(notification_tenant)
    outbox = NotificationOutbox.objects.get()

    process_notification(str(outbox.id))

    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.FAILED
    assert fake_providers["sms"].sent == []


def test_valid_e164_phone_is_accepted(make_rule, notification_tenant, fake_providers):
    from django_resaas.notifications.enums import Channel

    make_rule(channel=Channel.SMS, recipient_config={"phone": "+258841234567"})

    _emit(notification_tenant)
    outbox = NotificationOutbox.objects.get()

    process_notification(str(outbox.id))

    outbox.refresh_from_db()
    assert outbox.status == OutboxStatus.SENT
    assert len(fake_providers["sms"].sent) == 1


def test_custom_recipient_resolver_is_used(make_rule, notification_tenant):
    RecipientResolverRegistry.register(
        "sales.custom_customer",
        lambda ctx: [
            Recipient(type="customer", key="customer:42", email="customer@example.com")
        ],
    )

    make_rule(recipient_strategy="sales.custom_customer")

    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    assert outbox.recipient_identity == "customer@example.com"
    assert outbox.recipient_type == "customer"


def test_unregistered_resolver_yields_no_recipients(make_rule, notification_tenant):
    make_rule(recipient_strategy="does.not.exist")

    _emit(notification_tenant)

    assert NotificationOutbox.objects.count() == 0


def test_entity_admin_resolver(make_rule, notification_tenant):
    notification_tenant["entity"].admins.add(notification_tenant["user"])

    make_rule(recipient_strategy="entity_admin")

    _emit(notification_tenant)

    outbox = NotificationOutbox.objects.get()
    assert outbox.recipient_identity == notification_tenant["user"].email
