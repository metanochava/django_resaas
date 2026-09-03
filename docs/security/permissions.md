# Permissions

The backend is the final authority for authorization.

## Process

1.  Identify the view's action.
2.  Convert the action into a permission prefix.
3.  Get the model's technical name.
4.  Build the codename.
5.  Check it with `isPermited()`.

Example:

``` text
create + patient -> add_patient
update + patient -> change_patient
destroy + patient -> delete_patient
```

## Cache

A per-request cache can avoid repeated checks of the same codename
during the same request.

## Module

Besides the permission itself, the application can check whether the
corresponding module is active for the entity (see
[`../api/base-api-view.md`](../api/base-api-view.md)).

## Custom action permissions and ownership

`@resaas_action` methods get their own `Permission`, synced by
`ActionSyncService` into `ModelExtraAction`. Two fields decide what the
sync mechanism is and isn't allowed to touch:

- **`managed_by`** (`"decorator"` or `"manual"`, default `"manual"`) -
  identifies *who* owns a `ModelExtraAction` row. `ActionSyncService`
  always writes `managed_by="decorator"` for rows it creates/updates from
  a `@resaas_action`. A row created any other way (the admin, a data
  migration, directly in the shell) defaults to `"manual"` and is then
  **off-limits to the decorator**: if a `@resaas_action` is declared with
  the same `app`/`model`/`action` identity as an existing `managed_by="manual"`
  row, syncing raises `ImproperlyConfigured` instead of silently taking
  it over. To hand a manual action to the decorator on purpose, set
  `managed_by="decorator"` on that row yourself first.
- **`permission_managed`** (boolean, default `False`) - whether the
  *Permission itself* (not just the `ModelExtraAction` row) was created
  by RESAAS and is therefore safe to delete automatically once its
  action becomes an orphan (removed from code). A pre-existing
  `Permission` (created by a human, e.g. via the admin) is detected at
  sync time and marked `permission_managed=False`, so orphan cleanup
  removes the `ModelExtraAction` row but **never** the `Permission`.
  A `Permission` created via an explicit `@resaas_action(permission=...)`
  (meant to be shared/reused across actions) is likewise never deleted
  on cleanup, and its `.name` is never auto-renamed - only a permission
  following the default `{action}_{model}` naming convention has its
  `.name` kept in sync with the action's label/model automatically.

> [!NOTE]
> Orphan removal itself only ever happens in `ActionSyncService.sync_registry()` (the
> `post_migrate` signal / `manage.py sync_actions` entry point), which aggregates every
> registered view's declared actions *before* deciding what no longer exists anywhere in
> code. Calling `sync_view()` directly on a single view only upserts - it never deletes,
> since one view has no way of knowing whether a sibling view of the same model still
> declares an action it doesn't see. See `src/django_resaas/tests/test_permissions.py` and
> `test_action_sync.py` for the exact, tested behavior.
