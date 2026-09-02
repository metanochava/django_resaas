import fnmatch
import logging

from .payload import build_event_payload, build_object_ref

logger = logging.getLogger("django_resaas.events")


class EventDispatcher:
    """Generic, synchronous, in-process business-event dispatcher.

    django_resaas core never imports business models (Sale, Paciente,
    Employee, ...). It only ever sees: an event name, a tenant
    (entity/branch), an actor, a serializable object reference, and a
    context dict. Business apps are the ones that call `emit()`.

    `emit()` is NOT a queue - it runs every matching listener
    synchronously, in-process, inside whatever transaction the caller is
    in. This is deliberate: the NotificationEngine listener needs to
    create a NotificationOutbox row inside the *same* transaction.atomic()
    block as the business change that triggered it. The async boundary in
    this framework starts *after* that Outbox row is committed, never at
    the event layer - see notifications/outbox_dispatcher.py.

    Multiple, unrelated consumers can listen to the same events (the
    NotificationEngine is only one of them - audit trails, webhooks,
    analytics, ... may register their own listeners later). A listener
    that raises does NOT stop other listeners or bubble into the caller's
    transaction by default; pass `propagate=True` on `register()` for a
    listener whose failures *should* roll back the emitting transaction
    (the NotificationEngine uses this, since a broken rule should not
    silently swallow a notification write).
    """

    _listeners = []  # list[(pattern, callable, propagate)]

    # =========================================================
    # REGISTRATION
    # =========================================================

    @classmethod
    def register(cls, pattern, listener, *, propagate=False):
        """Register `listener(payload: dict)` for events matching `pattern`.

        `pattern` supports simple glob-style wildcards, e.g. "sales.*"
        matches "sales.sale.confirmed". An exact event name matches only
        itself.
        """

        cls._listeners.append((pattern, listener, propagate))

    @classmethod
    def unregister_all(cls):
        """Test helper: clear every registered listener."""

        cls._listeners = []

    # =========================================================
    # EMIT
    # =========================================================

    @classmethod
    def emit(
        cls,
        event,
        *,
        instance=None,
        entity_id=None,
        branch_id=None,
        actor=None,
        actor_id=None,
        context=None,
        occurrence_id=None,
    ):
        """Emit a business event synchronously to every matching listener.

        `instance`, when given, is used ONLY to derive entity_id/branch_id
        (if it exposes them, e.g. a BaseModel subclass) and the
        {app_label, model, pk} object reference - the instance itself is
        discarded immediately after and never reaches a listener.
        """

        obj = build_object_ref(instance)

        if instance is not None:
            entity_id = entity_id or getattr(instance, "entity_id", None)
            branch_id = branch_id or getattr(instance, "branch_id", None)

        if actor is not None and actor_id is None:
            actor_id = getattr(actor, "id", None)

        payload = build_event_payload(
            event,
            entity_id=entity_id,
            branch_id=branch_id,
            actor_id=actor_id,
            obj=obj,
            context=context,
            occurrence_id=occurrence_id,
        )

        for pattern, listener, propagate in cls._listeners:
            if not fnmatch.fnmatchcase(event, pattern):
                continue

            try:
                listener(payload)
            except Exception:
                if propagate:
                    raise

                logger.exception(
                    "EventDispatcher listener failed for event=%s pattern=%s",
                    event,
                    pattern,
                )

        return payload
