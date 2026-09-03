# Soft Delete, Restore and Hard Delete

Any model built on `SoftBaseModel` (which `BaseModel`/`TimeModel` both extend) gets soft delete
for free, backed by three managers: `objects` (alive rows only — the default), `all_objects`
(everything), `deleted_objects` (soft-deleted only).

## Deleting through the API

`DELETE .../<id>/` is a **soft** delete: `perform_destroy()` sets `deleted_at` (and stamps
`updated_by`) rather than removing the row. A soft-deleted row's plain `GET .../<id>/` then 404s —
it's no longer in the default `objects` manager — but the row still exists.

## Listing past the default manager

The `?objects=` query param switches which manager a list/retrieve endpoint reads from, always
still scoped to the current tenant:

```text
GET .../?objects=all       # active + soft-deleted
GET .../?objects=deleted   # soft-deleted only
```

Switching managers resets any tenant filtering already applied, which is why `get_queryset()`
re-applies the `entity_id`/`branch_id` filters immediately after the switch — see
[Request lifecycle](../architecture/request-lifecycle.md).

## Restore

```text
POST .../<id>/restore/
```

Looked up through `Model.all_objects`, filtered by `entity_id`/`branch_id` — restoring another
tenant's row 404s exactly like retrieving one does. Clears `deleted_at` and stamps `updated_by`.
Requires the `restore_<model>` permission.

## Hard delete

```text
DELETE .../<id>/hard_delete/
```

> [!WARNING]
> Permanently removes the row (bypasses `deleted_at` entirely) - there is no `restore` back
> from this. Same tenant-scoped lookup as restore. Requires the separate
> `hard_delete_<model>` permission — a group with only `delete_<model>` (soft delete) cannot
> hard-delete.

## Direct model usage

Outside the API, the same operations are available as instance methods:

```python
instance.delete(user=request.user)   # soft delete, stamps updated_by if the model has it
instance.restore(user=request.user)  # clears deleted_at, stamps updated_by
instance.hard_delete()               # real deletion
```
