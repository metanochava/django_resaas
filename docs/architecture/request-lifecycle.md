# Request Lifecycle

What actually runs, in order, for a request handled by a `BaseAPIView` subclass — grounded in
`core/base/views.py`.

```text
HTTP Request
   |
   v
TenantContextMiddleware        decodes X-RESAAS-Context / L (architecture/middleware.md)
   |
   v
initial()                      DRF's own initial() first, then RESAAS's checks:
   |
   +-- tenant_context_error set?        -> 403 PermissionDenied
   +-- tenant_context missing entirely? -> 403 PermissionDenied
   +-- ResaasContextService.validate_for_user(...)
   +-- request.entity_id missing?       -> 403 "not associated with any entity"
   +-- module_name active for entity?   -> 403 "Module '<name>' is not active"
   +-- permission codename granted?     -> 403 "Unauthorized" (cached per-request)
   |
   v
get_queryset()
   |
   +-- filter by entity_id / branch_id (if the model has them)
   +-- switch manager for ?objects=all / ?objects=deleted (if the model supports it)
   +-- re-apply entity_id / branch_id (switching manager resets any prior filtering)
   +-- apply_dynamic_search()  ->  build_search_query() from ?search=
   |
   v
DynamicFilterBackend + OrderingFilter    (api/filters-pagination.md)
   |
   v
Serializer  (BaseSerializer)
   |
   v
Model / Database
   |
   v
HTTP Response
```

## Create

`perform_create()` stamps `created_by`/`updated_by` from `request.user`, and — only for models
that actually have those columns — `entity_id`/`branch_id` from `request.entity_id`/
`request.branch_id`. This is the one and only place a `BaseModel` instance created through the API
gets its tenant set; outside the API (shell, management commands, signals, migrations), callers
must set `entity`/`branch` themselves or `BaseModel.save()` raises `ValidationError` — see
[Multi-tenancy](multi-tenancy.md#golden-rule-the-tenant-is-never-guessed).

```python
def perform_create(self, serializer):
    data = {"created_by": self.request.user, "updated_by": self.request.user}
    if hasattr(serializer.Meta.model, "entity_id"):
        data["entity_id"] = self.request.entity_id
    if hasattr(serializer.Meta.model, "branch_id"):
        data["branch_id"] = self.request.branch_id
    serializer.save(**data)
```

## Update

`perform_update()` only stamps `updated_by` — `entity`/`branch` are left untouched on update (a
row's tenant doesn't move when it's edited).

## Delete, restore, hard delete

`DELETE .../<id>/` calls `perform_destroy()`, which is a **soft** delete: it sets `deleted_at`
(and, via `instance.delete(user=...)`, `updated_by` too) rather than removing the row. Two
dedicated, separately-permissioned actions handle the rest — `POST .../<id>/restore/` and
`DELETE .../<id>/hard_delete/` — both looked up through `Model.all_objects` and still filtered by
`entity_id`/`branch_id`, so acting on another tenant's row 404s exactly like retrieving one does.
Full detail in [Soft delete](../features/soft-delete.md).
