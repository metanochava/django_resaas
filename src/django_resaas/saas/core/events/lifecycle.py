"""
Model lifecycle events: "<app_label>.<model>.<action>" emitted by the generic
CRUD of BaseAPIView (core/base/views.py) through the existing EventDispatcher.

Opt-in per model, in its RESAAS metadata:

    class RESAAS:
        lifecycle_events = True                     # every action below
        lifecycle_events = ["created", "updated"]   # only these

Actions: created, updated, deleted (soft), restored, hard_deleted.

Emitted from the API layer on purpose, not from Model.save() or Django
signals: those also run in the shell, migrations, imports and whenever a
listener saves again - which would repeat or recurse. A listener that writes
through the ORM never emits a lifecycle event, so a listener cannot loop.

Semantics (see docs/architecture/events.md):
- the write and the emit run in ONE transaction.atomic() block, the event
  right after the write;
- a listener registered with propagate=True that raises rolls the write back;
  any other listener's failure is logged and the write is kept;
- external effects (messages, HTTP calls) belong after the commit:
  transaction.on_commit() or the notifications Outbox, never inline;
- tenant (entity_id, branch_id) and actor come from the signed request
  context, never from the request body;
- every emission carries its own occurrence_id, so two writes of the same
  record are two occurrences (notification idempotency keys use it).
"""
import uuid

from django.apps import apps

from .dispatcher import EventDispatcher

LIFECYCLE_ACTIONS = ("created", "updated", "deleted", "restored", "hard_deleted")


def lifecycle_actions_for(Model):
    """The lifecycle actions `Model` opted into (empty when it did not)."""

    resaas = getattr(Model, "RESAAS", None)
    setting = getattr(resaas, "lifecycle_events", None) if resaas else None

    if setting is True:
        return set(LIFECYCLE_ACTIONS)
    if not setting:
        return set()

    unknown = set(setting) - set(LIFECYCLE_ACTIONS)
    if unknown:
        raise ValueError(
            f"{Model.__name__}.RESAAS.lifecycle_events: unknown action(s) {sorted(unknown)}; "
            f"supported: {list(LIFECYCLE_ACTIONS)}"
        )
    return set(setting)


def lifecycle_event_name(Model, action):
    return f"{Model._meta.app_label}.{Model._meta.model_name}.{action}"


def emit_lifecycle(request, instance, action, context=None):
    """Emit `action` for `instance` when its model opted in; returns the payload
    (or None). Call it inside the transaction of the write it describes."""

    Model = type(instance)
    if action not in lifecycle_actions_for(Model):
        return None

    return EventDispatcher.emit(
        lifecycle_event_name(Model, action),
        instance=instance,
        entity_id=getattr(request, "entity_id", None),
        branch_id=getattr(request, "branch_id", None),
        actor=getattr(request, "user", None),
        context={"lifecycle": action, **(context or {})},
        occurrence_id=str(uuid.uuid4()),
    )


def load_instance(payload):
    """The record a lifecycle payload points to, read again from the database
    and limited to the payload's own tenant (entity, and branch when the model
    has one). Soft-deleted rows are included (a "deleted" listener needs them).
    None when it does not exist (e.g. after hard_deleted) or belongs to another
    tenant."""

    ref = payload.get("object") or {}
    try:
        Model = apps.get_model(ref.get("app_label"), ref.get("model"))
    except (LookupError, ValueError, TypeError):
        return None

    manager = getattr(Model, "all_objects", Model._default_manager)
    queryset = manager.filter(pk=ref.get("pk"))

    if hasattr(Model, "entity_id"):
        if not payload.get("entity_id"):
            return None
        queryset = queryset.filter(entity_id=payload["entity_id"])

    if hasattr(Model, "branch_id") and payload.get("branch_id"):
        queryset = queryset.filter(branch_id=payload["branch_id"])

    return queryset.first()


def lifecycle_event_catalogue():
    """Every lifecycle event name the installed models opted into, sorted."""

    names = []
    for Model in apps.get_models():
        for action in lifecycle_actions_for(Model):
            names.append(lifecycle_event_name(Model, action))
    return sorted(names)
