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

## Managing group permissions

`Group` rows are **global**: the same group (e.g. the bootstrap `Admin`) can be linked to several
Entities (`EntityGroup`) and used as an EntityType template (`EntityTypeGroup`). Changing a group's
permissions changes them everywhere it is linked. For that reason `POST auth/permissions/setGroupPermissions/`
(`PermissionAPIView`, body `{"group": <id>, "permissions": [<id>, ...]}`, replaces the whole list)
is **PROTECTED** and checks, in order:

1. `change_group` in the current signed context, otherwise `403 permission_denied`.
2. Without `change_entitytype` (platform level, which only **Root** holds by default), the group must:
   - belong to the current Entity (`EntityGroup`), otherwise `404 group_not_in_entity`. A group of
     another Entity is not revealed.
   - be `editable`, otherwise `403 group_not_editable`. Only a group an Entity creates for itself
     (`EntityAPIView.createGroup`) is `editable=True`. Bootstrap and template groups are not, and
     clients cannot set the flag (read-only in `GroupSerializer`).
   - not be shared with another Entity nor be an EntityType template, otherwise `403 group_shared`.
3. **No escalation by delegation.** Every permission the request adds **or removes** must be held
   by the caller's active group, otherwise `403 permission_not_held` with
   `error.details.permissions` (ids). Permissions the list keeps unchanged are not checked,
   because the screen sends the whole list back.

The change runs in a transaction with the group row locked. The Root exception is carried by the
`change_entitytype` **permission**, never by the group's name.

The permission catalogue itself (`auth/permissions/`) can be listed by any authenticated user.
Creating, changing or deleting a `Permission` row needs `add_permission` / `change_permission` /
`delete_permission`.

A user's profiles in the current Branch are managed by `users/{id}/addGroup/` and `removeGroup/`
(`UserAPIView`, permission- and tenant-checked).

### Groups themselves (`auth/groups/`)

`GroupAPIView` applies the same rules (`saas/core/services/group_access_service.py`). Every action
needs its permission in the current context. An action without a mapped permission is denied.

| Action | Permission | Scope |
|---|---|---|
| `GET auth/groups/` | `list_group` | the current Entity's groups (all groups at platform level) |
| `GET auth/groups/{id}/`, `{id}/permissions/` | `view_group` | same; another Entity's group → `404` |
| `POST auth/groups/` | `add_group` | without platform level, the new group is linked to the current Entity and its Branches and is `editable=True` |
| `PUT/PATCH auth/groups/{id}/` | `change_group` | changeable group (rule 2 above) |
| `DELETE auth/groups/{id}/` | `delete_group` | changeable group; never the caller's active group (`400 cannot_delete_active_group`) |
| `POST {id}/addPermission/` | `change_group` | changeable group. A codename that already exists outside the `custom` content type → `409 permission_codename_exists` (authorization matches codenames, so it would grant the real capability). Creating a new custom permission needs `add_permission`; adding an existing custom one is a grant (rule 3). |
| `POST {id}/removePermission/` | `change_group` | changeable group; revoking needs the permission to be held (rule 3) |

### Removed endpoints

These endpoints were removed because they acted on any tenant with no permission check, and no
consumer used them:

| Removed | Use instead |
|---|---|
| `POST auth/permissions/{id}/addToGroup/`, `removeFromGroup/` | `setGroupPermissions/` |
| `POST auth/permissions/{id}/addToUser/`, `removeFromUser/` | `POST django_resaas/users/{id}/addGroup/`, `removeGroup/` |
| `GET django_resaas/resaasapps/{app}/{model}/data/` | the model's own `BaseAPIView` (tenant scope, action and field permissions) |

Tests: `src/django_resaas/saas/tests/test_permission_api_security.py`, `test_group_api_security.py`.

## Field-level permissions

A model can also gate individual fields (e.g. `Contract.salary`) with their own
`view`/`change` permissions, layered on top of the action permission - see
[Field-level permissions](field-permissions.md).

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
