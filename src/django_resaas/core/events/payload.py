"""
Serializable business-event payloads.

django_resaas core must never pass a live model instance, QuerySet or
lazy object into anything that could end up on a queue - only plain,
JSON-serializable dicts. This module is the single place that turns a
live instance (when the caller has one) into that dict.
"""


def build_object_ref(instance):
    """{'app_label': ..., 'model': ..., 'pk': ...} for a model instance.

    Never returns the instance itself - only these three strings.
    """

    if instance is None:
        return None

    meta = instance._meta

    return {
        "app_label": meta.app_label,
        "model": meta.model_name,
        "pk": str(instance.pk),
    }


def build_event_payload(
    event,
    *,
    entity_id,
    branch_id=None,
    actor_id=None,
    obj=None,
    context=None,
    occurrence_id=None,
    scheduled_at=None,
):
    """Build the plain-dict payload handed to every EventDispatcher listener.

    `obj`, if given, must already be a serializable {app_label, model, pk}
    dict (see build_object_ref) - never a model instance at this point.

    `scheduled_at`, if given, must be a timezone-aware `datetime` (same
    convention as any other Django datetime field) - stored as its ISO
    string, never the datetime object itself, to keep this payload plain
    JSON regardless of who ends up reading it.
    """

    return {
        "event": event,
        "entity_id": str(entity_id) if entity_id else None,
        "branch_id": str(branch_id) if branch_id else None,
        "actor_id": str(actor_id) if actor_id else None,
        "object": obj,
        "context": dict(context or {}),
        "occurrence_id": occurrence_id,
        "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
    }
