"""Entitlements: features, capacities and modules available to an
installation/tenant. See docs/security/entitlements.md."""
from django_resaas.saas.core.entitlements.provider import (  # noqa: F401
    EntitlementContext,
    EntitlementProvider,
    SettingsEntitlementProvider,
)
from django_resaas.saas.core.entitlements.service import (  # noqa: F401
    CapacityExceeded,
    FeatureNotAvailable,
    get_capacity,
    get_provider,
    get_usage,
    has_feature,
    has_module,
    require_capacity,
    require_feature,
    snapshot,
)
