"""Entitlement providers.

A provider answers three questions about the installation/tenant a request
runs in - never about the user (that is authorization, see permissions):

    has_feature(context, feature)   -> bool         is this functionality available?
    get_capacity(context, capacity) -> int | None   how much of it may be used? (None = no limit)
    has_module(context, module)     -> bool         may this business module run at all?

The framework ships one provider, SettingsEntitlementProvider. Another one
(database, license file, remote service, ...) only has to subclass
EntitlementProvider and be named in settings.RESAAS_ENTITLEMENT_PROVIDER; no
domain code changes. The core knows capabilities only - never commercial
plan names.
"""
from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class EntitlementContext:
    """Where the question is asked. Built from the signed tenant context, never
    from client-supplied ids."""

    entity_type_id: object = None
    entity_id: object = None
    branch_id: object = None


class EntitlementProvider:
    """Interface. The defaults answer "no restriction", so a subclass only
    overrides what it actually restricts."""

    def is_restricted(self, context):
        """False when this provider imposes nothing (everything available,
        no limits) - lets the frontend skip per-name checks."""
        return False

    def has_feature(self, context, feature):
        return True

    def get_capacity(self, context, capacity):
        return None

    def has_module(self, context, module):
        return True

    def features(self, context):
        """The features this provider knows, as {name: bool} (for the frontend)."""
        return {}

    def capacities(self, context):
        """The capacities this provider knows, as {name: limit} (for the frontend)."""
        return {}


class SettingsEntitlementProvider(EntitlementProvider):
    """Reads settings.RESAAS_ENTITLEMENTS:

        RESAAS_ENTITLEMENTS = {
            "features": {"multi_entity": False, "advanced_audit": True},
            "capacities": {"entities": 1, "branches": 3, "users": 20, "entity_types": 1},
            "modules": ["hr", "saude"],   # optional: business modules allowed
        }

    Not set (the default): nothing is restricted - existing installations keep
    their behaviour. Set: it fails closed - a feature it does not list is off,
    a capacity it does not list is 0. "modules" is optional: when present, a
    business module outside the list is refused (the framework's own apps
    always run); when absent, modules are only governed by App/EntityApp.
    """

    def _config(self):
        return getattr(settings, "RESAAS_ENTITLEMENTS", None)

    def is_restricted(self, context):
        return self._config() is not None

    def has_feature(self, context, feature):
        config = self._config()
        if config is None:
            return True
        return bool((config.get("features") or {}).get(feature, False))

    def get_capacity(self, context, capacity):
        config = self._config()
        if config is None:
            return None
        capacities = config.get("capacities") or {}
        return capacities.get(capacity, 0)

    def has_module(self, context, module):
        from django_resaas.saas.core.services.bootstrap_service import FRAMEWORK_MODULES

        config = self._config()
        if config is None or module in FRAMEWORK_MODULES:
            return True
        allowed = config.get("modules")
        return True if allowed is None else module in allowed

    def features(self, context):
        config = self._config() or {}
        return {name: bool(on) for name, on in (config.get("features") or {}).items()}

    def capacities(self, context):
        config = self._config() or {}
        return dict(config.get("capacities") or {})
