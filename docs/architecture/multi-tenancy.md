# Multi-tenancy

RESAAS works with a tenant context, carried on every authenticated request
as two headers:

- `X-RESAAS-Context` - a signed token (see `ResaasContextService`,
  `TenantContextMiddleware`) that decodes into `entity_type_id`,
  `entity_id`, `branch_id` and `group_id`.
- `L` - the active language id, read independently into `request.lang_id`.

`TenantContextMiddleware` runs on every request and always initializes all
five of `request.entity_type_id` / `entity_id` / `branch_id` / `group_id` /
`lang_id`, defaulting to `None` when the header is absent or fails to
decode (the failure itself is captured into `request.tenant_context_error`,
never raised) - see [`middleware.md`](middleware.md).

## Golden rule: the tenant is never guessed

**`django_resaas` never picks a tenant automatically.** A `BaseModel`
subclass (any model with both `entity`/`branch` FKs) requires them to be
set *explicitly* before `.save()` - there is no fallback to "the first
Entity" or "the first Branch". If either is missing, `save()` raises
`django.core.exceptions.ValidationError` immediately; nothing gets
written to the wrong tenant by accident.

```python
# core/base/models.py
def ensure_tenant(self):
    if not self.entity_id or not self.branch_id:
        raise ValidationError(
            f"{self.__class__.__name__} requires an explicit "
            "entity and branch before it can be saved - "
            "automatic tenant selection is not supported."
        )
```

In the API path, `BaseAPIView.perform_create()` sets `entity`/`branch`
explicitly from `request.entity_id`/`request.branch_id` before saving, so
this never surfaces for a normal authenticated request. It DOES surface -
deliberately - for anything that constructs a `BaseModel` instance without
going through the API: shell sessions, management commands, Celery tasks,
signals, data migrations, fixtures. Those call sites must set `entity`/
`branch` explicitly themselves; see
`src/django_resaas/tests/test_tenant.py` for the exact behavior this
locks in (including that it never borrows another tenant's branch either).

## Main rule (querying)

A model that has `entity_id` must be filtered by the active entity.
A model that has `branch_id` must also be filtered by the active branch.

Conceptual example:

``` python
if hasattr(Model, "entity_id"):
    qs = qs.filter(entity_id=self.request.entity_id)

if hasattr(Model, "branch_id"):
    qs = qs.filter(branch_id=self.request.branch_id)
```

When the manager is swapped, for example to `all_objects` or
`deleted_objects`, the tenant filters must be reapplied.

## Purpose

The goal is to prevent a request from one entity from accidentally
accessing data belonging to another entity.
