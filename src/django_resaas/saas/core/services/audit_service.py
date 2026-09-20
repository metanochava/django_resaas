"""One place that writes AuditLog rows (who did what to which record, in which
entity, from where). Never put secrets in an event - only ids and codes."""
from django_resaas.saas.core.tenant.current import current_entity_id
from django_resaas.saas.models.audit_log import AuditLog


def client_ip(request):
    if request is None:
        return None

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")

    return ip or None


def record(*, action, target, actor=None, request=None, entity_id=None):
    """
    action  a short event code (<= 50 chars), e.g. "TEMPORARY_PASSWORD_VIEWED"
    target  the model instance the event is about
    actor   who did it (None: the system, e.g. a scheduled expiry)
    """
    entity_id = entity_id or getattr(request, "entity_id", None) or current_entity_id()

    return AuditLog.objects.create(
        user=actor if getattr(actor, "pk", None) else None,
        action=action,
        model=type(target).__name__,
        object_id=str(target.pk),
        entity_id=entity_id,
        ip_address=client_ip(request),
    )
