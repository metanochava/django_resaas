# BaseAPIView

`BaseAPIView` is the common base for the REST APIs.

## Main responsibilities

-   CRUD through `ModelViewSet`;
-   filters;
-   ordering;
-   dynamic search;
-   permissions;
-   multi-tenancy;
-   auditing;
-   soft delete;
-   restore;
-   hard delete;
-   select mode.

## Permission mapping

Example:

``` python
permission_action_map = {
    "list": "list",
    "retrieve": "view",
    "create": "add",
    "update": "change",
    "partial_update": "change",
    "destroy": "delete",
    "restore": "restore",
    "hard_delete": "hard_delete",
}
```

For a `Patient` model, creation may require `add_patient`, updating
`change_patient` and removal `delete_patient`.

## Queryset

`get_queryset()` must be the central point that guarantees tenant
isolation before listing and search. Its own list is: apply
`entity_id`/`branch_id` filters -> switch manager for `?objects=` if
requested -> **re-apply** `entity_id`/`branch_id` (the switched manager
isn't tenant-scoped by itself) -> apply dynamic search.

## `?objects=` (soft delete)

Every `BaseModel`/`SoftBaseModel` uses a soft-delete manager by default
(`.objects` only returns non-deleted rows). The list/retrieve endpoints
accept a query param to look past that, always still tenant-scoped:

- `?objects=all` - uses `Model.all_objects` (active + soft-deleted).
- `?objects=deleted` - uses `Model.deleted_objects` (soft-deleted only).
- absent - the normal `.objects` manager (active only).

Deleting through the API (`DELETE .../<id>/`) is a **soft** delete
(`instance.delete()` sets `deleted_at`). Two dedicated actions handle the
rest:

- `POST .../<id>/restore/` - clears `deleted_at`. Looked up through
  `all_objects`, still filtered by `entity_id`/`branch_id`, so restoring
  another tenant's row 404s exactly like retrieving one does.
- `DELETE .../<id>/hard_delete/` - permanently removes the row (same
  tenant-scoped lookup).

See `src/django_resaas/tests/test_soft_delete.py` for the exact,
tested behavior (including that a soft-deleted row's plain
`GET .../<id>/` 404s, but `GET .../<id>/?objects=all` succeeds).

## Module activation

`initial()` requires `self.module_name` to be set (via `@registerView(...)`
- see [`../development/creating-resource.md`](../development/creating-resource.md))
and checks `EntityApp.objects.filter(entity_id=request.entity_id,
app__name=module_name, state="Active").exists()` before anything else
runs. A view without `module_name` set, or a tenant that hasn't activated
that module, gets rejected before the queryset is ever touched - see
`src/django_resaas/tests/test_module_activation.py`.

## Search, filters, pagination

- Search: `?search=...` matches `RESAAS.search_fields` when the model
  declares them, otherwise falls back to every `Char/Text/EmailField`
  plus simple `ForeignKey.name` lookups.
- Filters: `DjangoFilterBackend` + `OrderingFilter` are always active
  (see [`filters-pagination.md`](filters-pagination.md)).
- Pagination: `ResaasPagination` (`DEFAULT_PAGINATION_CLASS`), whose
  `page_size` a model can override via `RESAAS.pagination` - this is
  what `Schema 1.0`'s `pagination.page_size` reflects
  (see [`schema-contract.md`](schema-contract.md)).

## Custom actions

`@resaas_action(...)` methods declared on a `BaseAPIView` subclass become
both real DRF actions (routable, permission-checked) and entries in
`Schema 1.0`'s `actions` list, kept in sync by `ActionSyncService` - see
[`../development/creating-resource.md`](../development/creating-resource.md)
for the decorator's arguments and the manual/decorator ownership rules,
and [`schema-contract.md`](schema-contract.md) for the exact shape the
frontend receives.
