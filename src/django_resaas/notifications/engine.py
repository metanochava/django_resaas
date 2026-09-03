"""
NotificationEngine - the orchestrator wired to EventDispatcher in
NotificationsConfig.ready(). Turns one business-event payload into zero
or more durable NotificationOutbox rows, synchronously, inside whatever
transaction the emitting business code is in.

Pipeline per the plan: rule -> module active? -> conditions -> recipient
resolution -> channel enabled? -> preferences/consent -> template ->
NotificationOutbox.objects.get_or_create(idempotency_key=...).

Never calls a provider. Never queues anything itself - that's
OutboxDispatcher's job, triggered by the caller via transaction.on_commit
after this returns (see notifications/outbox_dispatcher.py).
"""

import logging

from django.apps import apps as django_apps
from django.conf import settings
from django.db.models import Q
from django.utils.dateparse import parse_datetime

from django_resaas.notifications.conditions import evaluate
from django_resaas.notifications.enums import Category, Channel, OutboxStatus
from django_resaas.notifications.recipients import (
    RecipientResolverRegistry,
    ResolverContext,
)
from django_resaas.notifications.rendering import (
    is_valid_e164,
    is_valid_email,
    pick_template,
    render_template,
    resolve_language_code,
)
from django_resaas.notifications.retry import max_attempts

logger = logging.getLogger("django_resaas.notifications")


class _RuleChannelView:
    """Tiny read-only shim so _consent_allowed() can be reused for a
    fallback channel without mutating (or copying) the real rule row -
    only `.channel` differs from the wrapped rule, everything else
    (entity_id, category, ...) is read straight through."""

    def __init__(self, rule, channel):
        self._rule = rule
        self.channel = channel

    def __getattr__(self, name):
        return getattr(self._rule, name)


class NotificationEngine:

    # =========================================================
    # ENTRY POINT (registered with EventDispatcher in apps.py)
    # =========================================================

    @classmethod
    def on_event(cls, payload):
        if not getattr(settings, "NOTIFICATIONS_ENABLED", False):
            return  # system-wide kill switch (opt-in, spec section 2)

        entity_id = payload.get("entity_id")
        if not entity_id:
            # Can't resolve tenant-scoped rules without a tenant - never
            # guess/fallback to "the first Entity" (spec section 64).
            return

        from django_resaas.notifications.models import NotificationRule

        rules = NotificationRule.objects.filter(
            entity_id=entity_id,
            event=payload["event"],
            enabled=True,
        ).filter(Q(branch_id=payload.get("branch_id")) | Q(branch_id__isnull=True))

        for rule in rules:
            cls._process_rule(rule, payload)

    # =========================================================
    # RULE -> RECIPIENTS
    # =========================================================

    @classmethod
    def _process_rule(cls, rule, payload):
        if not cls._module_active(rule):
            return

        obj = cls._resolve_object(payload.get("object"))

        condition_data = {
            **(payload.get("context") or {}),
            "object": obj,
            "actor_id": payload.get("actor_id"),
        }

        if not evaluate(rule.conditions, condition_data):
            return

        actor = cls._resolve_user(payload.get("actor_id"))

        ctx = ResolverContext(
            payload=payload,
            rule=rule,
            obj=obj,
            actor=actor,
            recipient_config=rule.recipient_config or {},
        )

        recipients = RecipientResolverRegistry.resolve(rule.recipient_strategy, ctx)

        for recipient in recipients:
            cls._process_recipient(rule, payload, recipient, obj)

    # =========================================================
    # RECIPIENT -> OUTBOX
    # =========================================================

    @classmethod
    def _process_recipient(cls, rule, payload, recipient, obj):
        if not cls._channel_enabled(rule):
            return

        if not cls._consent_allowed(rule, recipient):
            return

        identity = recipient.email if rule.channel == Channel.EMAIL else recipient.phone
        if not identity:
            return  # recipient simply has no usable address for this channel

        notif_settings = cls._get_settings(rule)
        language_code = resolve_language_code(recipient.language_code, notif_settings)

        template = pick_template(rule, language_code)
        if not template:
            logger.warning(
                "NotificationRule %s has no template for language=%s - skipping",
                rule.id,
                language_code,
            )
            return

        subject, body = render_template(
            template,
            {
                **(payload.get("context") or {}),
                "object": obj,
                "recipient": recipient,
                "entity": rule.entity,
            },
        )

        cls._create_outbox(rule, payload, recipient, identity, subject, body)

    # =========================================================
    # OUTBOX CREATION (idempotent)
    # =========================================================

    @classmethod
    def _create_outbox(cls, rule, payload, recipient, identity, subject, body):
        from django_resaas.notifications.models import NotificationOutbox

        occurrence_id = payload.get("occurrence_id") or "{}:{}".format(
            payload["event"], (payload.get("object") or {}).get("pk") or "-"
        )

        idempotency_key = ":".join(
            [
                str(rule.entity_id),
                str(rule.id),
                rule.channel,
                recipient.key,
                occurrence_id,
            ]
        )

        defaults = {
            "entity_id": rule.entity_id,
            "branch_id": payload.get("branch_id") or rule.branch_id,
            "created_by_id": payload.get("actor_id"),
            "updated_by_id": payload.get("actor_id"),
            "event": payload["event"],
            "rule": rule,
            "channel": rule.channel,
            "category": rule.category,
            "priority": rule.priority,
            "recipient_type": recipient.type,
            "recipient_identity": identity,
            "recipient_reference": recipient.key,
            "subject": subject,
            "body": body,
            "provider": rule.provider,
            "status": OutboxStatus.PENDING,
            "max_attempts": max_attempts(),
            "metadata": {
                "object": payload.get("object"),
                "occurrence_id": occurrence_id,
                "actor_id": payload.get("actor_id"),
                # Kept so a failed send can fall back to a different
                # channel for the *same* recipient (spec section 53) -
                # the Outbox itself only snapshots one resolved
                # identity, so the alternate address has to live here.
                "recipient_email": recipient.email,
                "recipient_phone": recipient.phone,
            },
        }

        scheduled_at = cls._resolve_scheduled_at(payload.get("scheduled_at"))
        if scheduled_at:
            defaults["scheduled_at"] = scheduled_at

        outbox, created = NotificationOutbox.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults=defaults,
        )

        if created:
            from django.db import transaction

            from django_resaas.notifications.outbox_dispatcher import OutboxDispatcher

            transaction.on_commit(lambda: OutboxDispatcher.try_dispatch(outbox.id))

        return outbox

    # =========================================================
    # FALLBACK (spec sections 53-54) - triggered from tasks.py on a
    # permanent/final failure, never proactively.
    # =========================================================

    @classmethod
    def create_fallback_outbox(cls, outbox):
        """Best-effort channel fallback for one failed Outbox row. Off
        unless the rule explicitly set fallback_channel. Re-checks
        channel-enabled + consent for the FALLBACK channel - never
        bypasses opt-out just because the original channel failed
        (spec section 54). Never chains (a fallback outbox never gets
        its own fallback)."""

        from django_resaas.notifications.models import NotificationOutbox
        from django_resaas.notifications.recipients import Recipient

        rule = outbox.rule
        if not rule or not rule.fallback_channel:
            return None

        if rule.fallback_channel == outbox.channel:
            return None

        if outbox.metadata.get("is_fallback"):
            return None

        recipient = Recipient(
            type=outbox.recipient_type,
            key=outbox.recipient_reference or "",
            email=outbox.metadata.get("recipient_email"),
            phone=outbox.metadata.get("recipient_phone"),
        )

        if not cls._channel_enabled_for(rule, rule.fallback_channel):
            return None

        fallback_category_rule = _RuleChannelView(rule, rule.fallback_channel)
        if not cls._consent_allowed(fallback_category_rule, recipient):
            return None

        identity = (
            recipient.email
            if rule.fallback_channel == Channel.EMAIL
            else recipient.phone
        )
        if not identity:
            return None

        idempotency_key = f"{outbox.idempotency_key}:fallback:{rule.fallback_channel}"

        fallback, created = NotificationOutbox.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                "entity_id": outbox.entity_id,
                "branch_id": outbox.branch_id,
                "created_by_id": outbox.created_by_id,
                "updated_by_id": outbox.updated_by_id,
                "event": outbox.event,
                "rule": rule,
                "channel": rule.fallback_channel,
                "category": outbox.category,
                "priority": outbox.priority,
                "recipient_type": recipient.type,
                "recipient_identity": identity,
                "recipient_reference": recipient.key,
                "subject": (
                    outbox.subject if rule.fallback_channel == Channel.EMAIL else None
                ),
                "body": outbox.body,
                "provider": None,
                "status": OutboxStatus.PENDING,
                "max_attempts": max_attempts(),
                "metadata": {
                    **{
                        k: v
                        for k, v in outbox.metadata.items()
                        if k
                        in (
                            "object",
                            "occurrence_id",
                            "actor_id",
                            "recipient_email",
                            "recipient_phone",
                        )
                    },
                    "is_fallback": True,
                    "original_outbox_id": str(outbox.id),
                },
            },
        )

        if created:
            from django.db import transaction

            from django_resaas.notifications.outbox_dispatcher import OutboxDispatcher

            transaction.on_commit(lambda: OutboxDispatcher.try_dispatch(fallback.id))

        return fallback

    @classmethod
    def _channel_enabled_for(cls, rule, channel):
        notif_settings = cls._get_settings(rule)
        if not notif_settings:
            return False
        return bool(getattr(notif_settings, f"{channel}_enabled", False))

    # =========================================================
    # GATES
    # =========================================================

    @classmethod
    def _module_active(cls, rule):
        from django_resaas.engine.models.entity_app import EntityApp

        return EntityApp.objects.filter(
            entity__id=rule.entity_id,
            app__name=rule.module,
            state="Active",
        ).exists()

    @classmethod
    def _get_settings(cls, rule):
        from django_resaas.notifications.models import NotificationSettings

        if rule.branch_id:
            settings_row = NotificationSettings.objects.filter(
                entity_id=rule.entity_id, branch_id=rule.branch_id
            ).first()
            if settings_row:
                return settings_row

        return NotificationSettings.objects.filter(
            entity_id=rule.entity_id, branch__isnull=True
        ).first()

    @classmethod
    def _channel_enabled(cls, rule):
        notif_settings = cls._get_settings(rule)
        if not notif_settings:
            return False  # no settings row at all = nothing configured = opt-in default off

        return bool(getattr(notif_settings, f"{rule.channel}_enabled", False))

    @classmethod
    def _consent_allowed(cls, rule, recipient):
        from django_resaas.notifications.models import NotificationPreference

        preference = NotificationPreference.objects.filter(
            entity_id=rule.entity_id,
            recipient_type=recipient.type,
            recipient_key=recipient.key,
            channel=rule.channel,
            category=rule.category,
        ).first()

        if rule.category == Category.MARKETING:
            return bool(preference and preference.enabled)

        if preference and not preference.enabled:
            return False  # explicit opt-out always respected

        return True

    # =========================================================
    # RESOLUTION HELPERS
    # =========================================================

    @staticmethod
    def _resolve_object(object_ref):
        if not object_ref:
            return None

        try:
            model = django_apps.get_model(object_ref["app_label"], object_ref["model"])
            return model.objects.filter(pk=object_ref["pk"]).first()
        except (LookupError, KeyError):
            return None

    @staticmethod
    def _resolve_user(user_id):
        if not user_id:
            return None

        from django_resaas.engine.models.user import User

        return User.objects.filter(id=user_id).first()

    @staticmethod
    def _resolve_scheduled_at(value):
        """`payload["scheduled_at"]` is always a plain ISO string (or
        None) by the time it gets here - EventDispatcher.emit() never
        lets a live datetime past build_event_payload() either, for the
        same "payload must stay a plain, serializable dict" reason every
        other field on it does (spec section 5)."""

        if not value:
            return None

        return parse_datetime(value)
