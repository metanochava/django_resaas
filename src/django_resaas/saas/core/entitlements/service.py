"""Entitlement checks: the API the rest of the code calls.

    has_feature(request, "multi_entity")                 -> bool
    require_feature(request, "multi_entity")             -> raises 403 feature_not_available
    get_capacity(request, "branches")                    -> int | None (None = no limit)
    require_capacity(request, "branches")                -> raises 403 capacity_exceeded
    has_module(request, "hr")                            -> bool

`request` may also be an EntitlementContext. The context always comes from the
signed tenant context the middleware put on the request - never from ids in
the body.

Entitlements are not permissions: a request must pass both. Permission says
whether the user may do the operation; an entitlement says whether this
installation/tenant has the functionality, and how much of it.

A provider that raises is treated as "no": the feature is off, the capacity is
0, the module is refused (fail closed), and the error is logged.
"""
import logging

from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.utils.module_loading import import_string

from django_resaas.saas.core.entitlements.provider import (
    EntitlementContext,
    SettingsEntitlementProvider,
)
from django_resaas.saas.core.exceptions.errors import ResaasAPIException

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = "django_resaas.saas.core.entitlements.provider.SettingsEntitlementProvider"

_provider = None


def get_provider():
    global _provider
    if _provider is None:
        path = getattr(settings, "RESAAS_ENTITLEMENT_PROVIDER", None) or DEFAULT_PROVIDER
        _provider = import_string(path)()
    return _provider


@receiver(setting_changed)
def _reset_provider(setting, **kwargs):
    global _provider
    if setting in ("RESAAS_ENTITLEMENT_PROVIDER", "RESAAS_ENTITLEMENTS"):
        _provider = None


class FeatureNotAvailable(ResaasAPIException):
    status_code = 403
    translate_details = False  # feature/capacity names and limits are machine values
    default_detail = "This feature is not available."


class CapacityExceeded(ResaasAPIException):
    status_code = 403
    translate_details = False  # feature/capacity names and limits are machine values
    default_detail = "The usage limit for this resource has been reached."


def context_of(request_or_context):
    if isinstance(request_or_context, EntitlementContext):
        return request_or_context
    request = request_or_context
    return EntitlementContext(
        entity_type_id=getattr(request, "entity_type_id", None),
        entity_id=getattr(request, "entity_id", None),
        branch_id=getattr(request, "branch_id", None),
    )


def _ask(method, context, name, denied):
    try:
        return getattr(get_provider(), method)(context, name)
    except Exception:
        logger.exception("Entitlement provider failed on %s(%r); denying.", method, name)
        return denied


def has_feature(request_or_context, feature):
    return bool(_ask("has_feature", context_of(request_or_context), feature, False))


def require_feature(request_or_context, feature):
    if not has_feature(request_or_context, feature):
        raise FeatureNotAvailable(
            "This feature is not available.",
            code="feature_not_available",
            details={"feature": feature},
        )


def get_capacity(request_or_context, capacity):
    return _ask("get_capacity", context_of(request_or_context), capacity, 0)


def has_module(request_or_context, module):
    return bool(_ask("has_module", context_of(request_or_context), module, False))


# ---------------------------------------------------------------- usage

def _count_entities(context):
    from django_resaas.saas.models.entity import Entity
    return Entity.objects.count()


def _count_entity_types(context):
    from django_resaas.saas.models.entity_type import EntityType
    return EntityType.objects.count()


def _count_branches(context):
    from django_resaas.saas.models.branch import Branch
    return Branch.objects.filter(entity_id=context.entity_id).count()


def _count_users(context):
    from django_resaas.saas.models.entity_user import EntityUser
    return EntityUser.objects.filter(entity_id=context.entity_id, state="Active").count()


# The capacities the framework itself counts and enforces. entities and
# entity_types are installation-wide; branches and users are per Entity.
USAGE_COUNTERS = {
    "entities": _count_entities,
    "entity_types": _count_entity_types,
    "branches": _count_branches,
    "users": _count_users,
}


def get_usage(request_or_context, capacity):
    counter = USAGE_COUNTERS.get(capacity)
    return counter(context_of(request_or_context)) if counter else None


def require_capacity(request_or_context, capacity, current=None, adding=1):
    """Raise CapacityExceeded unless `adding` more fit under the limit.

    `current` is the usage now; omitted, it is counted with USAGE_COUNTERS
    (a capacity the framework does not count must pass it). Call it inside the
    transaction that creates the rows; for per-Entity capacities lock the
    Entity row first (select_for_update) so two concurrent requests cannot
    both take the last slot."""
    context = context_of(request_or_context)
    limit = get_capacity(context, capacity)
    if limit is None:
        return

    if current is None:
        current = get_usage(context, capacity)
        if current is None:
            raise ValueError(f"No usage counter for capacity {capacity!r}: pass current=")

    if current + adding > limit:
        raise CapacityExceeded(
            "The usage limit for this resource has been reached.",
            code="capacity_exceeded",
            details={"capacity": capacity, "limit": limit, "current": current},
        )


def snapshot(request_or_context):
    """What the frontend needs for UX: whether anything is restricted, the
    known features and each capacity's limit and current usage."""
    context = context_of(request_or_context)
    provider = get_provider()

    try:
        restricted = provider.is_restricted(context)
        features = provider.features(context)
        limits = provider.capacities(context)
    except Exception:
        logger.exception("Entitlement provider failed while describing the context; denying.")
        restricted, features, limits = True, {}, {}

    capacities = {}
    for name in sorted(set(USAGE_COUNTERS) | set(limits)):
        limit = get_capacity(context, name)
        capacities[name] = {"limit": limit, "used": get_usage(context, name)}

    return {"restricted": restricted, "features": features, "capacities": capacities}
