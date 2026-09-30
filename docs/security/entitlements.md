# Entitlements: features, capacities and modules

## What

An **entitlement** says what an installation or tenant may use:

| Concept | Question it answers | Example |
|---|---|---|
| **Feature** | Is this functionality available here? | `multi_entity`, `advanced_audit` |
| **Capacity** | How much of it may be used? | `branches = 3`, `users = 20` |
| **Module** | May this business module run at all? | `hr`, `saude` |

It is **not** authorization. The other layers stay as they are:

| Layer | Question |
|---|---|
| Permission | May *this user* perform this operation? ([Permissions](permissions.md)) |
| Entitlement | Does *this installation/tenant* have the functionality, and how much of it? |
| Object scope | On which objects may the user operate? |
| Tenant | Within which Entity/Branch? ([Multi-tenancy](../architecture/multi-tenancy.md)) |
| Module activation | Is the module switched on for the Entity? (`App`/`EntityApp`) |

A request must pass **all** of them. An entitlement never grants a permission,
and a permission never lifts an entitlement.

The core knows capabilities only. Commercial products or plans ("Business",
"Enterprise", ...) are outside the framework: whoever sells them turns a plan
into features and capacities through a provider.

## Why

`App`/`EntityApp` turns modules on per Entity, but cannot express limits such as
"3 branches" or "20 users", and it should not become a pricing system. The
entitlement layer adds that, behind a replaceable provider, without new models
or migrations.

## Configuration

By default nothing is restricted: an installation that does not configure
entitlements behaves exactly as before.

```python
# settings.py
RESAAS_ENTITLEMENTS = {
    "features": {"multi_entity": False, "advanced_audit": True},
    "capacities": {"entities": 1, "branches": 3, "users": 20, "entity_types": 1},
    "modules": ["hr", "saude"],          # optional
}
```

- Once `RESAAS_ENTITLEMENTS` is set, it **fails closed**:
  - a feature it does not list is **off**;
  - a capacity it does not list is **0**.
- A capacity of `None` means no limit.
- `"modules"` is optional:
  - when present, a business module outside the list is refused;
  - the framework's own apps (`django_resaas`, `notifications`) always run;
  - when absent, modules are governed only by `App`/`EntityApp`.

### Providers

`SettingsEntitlementProvider` (the default) reads the setting above. To take
entitlements from somewhere else (database, license file, remote service),
subclass `EntitlementProvider` and name the class in
`RESAAS_ENTITLEMENT_PROVIDER`. Domain code does not change.

```python
# myproject/entitlements.py
from django_resaas.saas.core.entitlements import EntitlementProvider

class LicenseEntitlementProvider(EntitlementProvider):
    def is_restricted(self, context):
        return True

    def has_feature(self, context, feature):
        return feature in load_license().features

    def get_capacity(self, context, capacity):
        # context.entity_type_id / entity_id / branch_id: answer per tenant if needed
        return load_license().limits.get(capacity, 0)

    def has_module(self, context, module):
        return module in load_license().modules

    def features(self, context):             # for GET resaas/entitlements/
        return {name: True for name in load_license().features}

    def capacities(self, context):
        return dict(load_license().limits)

# settings.py
RESAAS_ENTITLEMENT_PROVIDER = "myproject.entitlements.LicenseEntitlementProvider"
```

The base class answers "no restriction" for every method, so a provider only
overrides what it restricts.

## Usage (backend)

```python
from django_resaas.saas.core.entitlements import (
    has_feature, require_feature, get_capacity, require_capacity, has_module,
)

if has_feature(request, "advanced_audit"):
    ...

require_feature(request, "multi_entity")          # 403 feature_not_available

require_capacity(request, "branches")             # counts the current usage itself
require_capacity(request, "invoices_per_month", current=count_this_month())
```

- `request` may also be an `EntitlementContext(entity_type_id, entity_id,
  branch_id)`, for code that runs outside a request, or for a tenant being created.
- The context is always taken from the **signed** RESAAS context
  (`request.entity_id`, ...), never from ids in the body.
- `require_capacity(name, current=None, adding=1)` refuses when
  `current + adding > limit`. At `limit` there is no room left.
- For `entities`, `entity_types`, `branches` and `users` the framework counts
  `current` itself. For any other capacity pass `current=`, or a `ValueError`
  is raised.
- Call it inside the transaction that creates the rows.
- For a per-Entity capacity, lock the Entity row first
  (`Entity.objects.select_for_update()`), so that two concurrent requests
  cannot both take the last slot. The core does this at every point listed below.

### What the core enforces

| Capacity | Counted as | Checked by |
|---|---|---|
| `entities` | live Entities (installation) | `POST /api/django_resaas/entitys/` |
| `entity_types` | live EntityTypes (installation) | `POST /api/django_resaas/entitytypes/` |
| `branches` | Branches of the current Entity | `POST /api/django_resaas/branchs/`; the main Branch created with a new Entity |
| `users` | **active** `EntityUser` rows of the Entity | user creation (`POST /api/django_resaas/users/`), `entitys/<id>/addUser/`, a group assignment that brings a user into the Entity |

Platform setup is not limited: `create_root`, `BootstrapService` and management
commands create the first Entity, Branch and EntityType.

Module entitlements are checked together with module activation. Activation
and the entitlement are ANDed: an entitlement never activates a module.
The check is applied in:
- `BaseAPIView.initial()` (403 `module_not_available`);
- the menus (`GET /api/django_resaas/users/<id>/menus/`);
- the dashboards (`is_module_active`);
- the notification rules.

The installation-wide counts (`entities`, `entity_types`) are not serialised by
a lock. Two administrators creating the last Entity at the same instant could
both succeed. These operations are rare and platform-level.

## API

### `GET /api/resaas/entitlements/` (PROTECTED)

**Access.** Authentication plus a valid signed RESAAS context
(`X-RESAAS-Context`). There is no permission codename: it describes the
caller's own tenant.

**Response (200)**, when nothing is restricted:

```json
{"restricted": false, "features": {},
 "capacities": {"branches": {"limit": null, "used": 1}, "entities": {"limit": null, "used": 4},
                "entity_types": {"limit": null, "used": 2}, "users": {"limit": null, "used": 3}}}
```

**Response (200)**, with limits (`used` is the current tenant's usage for
`branches` and `users`, and the installation's usage for `entities` and `entity_types`):

```json
{"restricted": true, "features": {"multi_entity": false, "advanced_audit": true},
 "capacities": {"branches": {"limit": 3, "used": 3}, "users": {"limit": 20, "used": 4}, "...": {}}}
```

**Errors.**
- 401 when not authenticated.
- 403 without a context, or with an invalid or expired one.

### Errors of enforced operations

| Status | `error.code` | `error.details` |
|---|---|---|
| 403 | `feature_not_available` | `{"feature": "multi_entity"}` |
| 403 | `capacity_exceeded` | `{"capacity": "branches", "limit": 3, "current": 3}` |
| 403 | `module_not_available` | `null` |

`error.message` is translated. The values in `details` are machine values:
they are never translated, and numbers stay numbers. See
[Errors and alerts](../api/errors-and-alerts.md).

## Security

- **Enforcement is backend only.** The frontend reads the snapshot for UX
  (hide, disable, show "3 / 3"). A client that ignores it and calls the API
  directly is refused the same way (`test_hiding_the_button_is_not_the_protection`).
- **Superusers and entity administrators are subject to capacities.** A limit
  is not a permission.
- **A failing provider is treated as a denial.** When it raises, the feature is
  off, the capacity is 0 and the module is refused, and the error is logged.
- **Order in a request:** authentication → tenant context → permission of the
  action → capacity (at creation) → the business operation. Permission is
  checked first, so a caller without the permission gets 403
  `permission_denied` and learns nothing about the limits.

## Frontend

`quasar_resaas` exposes `useEntitlementStore()`:
- `load()`;
- `hasFeature(name)`;
- `getCapacity(name)`;
- `canAdd(name)`.

See quasar_resaas
[Entitlements](https://github.com/metanochava/quasar_resaas/blob/main/docs/quasar-resaas/features/entitlements.md).

## Troubleshooting

| Symptom | Check |
|---|---|
| Every business module answers 403 `module_not_available` | `RESAAS_ENTITLEMENTS["modules"]` lists the module's **App name**, e.g. `"hr"` |
| Creating anything answers `capacity_exceeded` right after enabling entitlements | Unlisted capacities are 0 once `RESAAS_ENTITLEMENTS` is set: list every capacity (use `None` for no limit) |
| `ValueError: No usage counter for capacity ...` | A custom capacity needs `require_capacity(..., current=...)` |
| Limits ignored | A custom `RESAAS_ENTITLEMENT_PROVIDER` whose `get_capacity` returns `None` (no limit) |

Tests: `saas/tests/test_entitlements.py`.
