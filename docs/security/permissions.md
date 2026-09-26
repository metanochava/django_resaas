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

## Profile templates (`group_creator`)

Modules ship default profiles (Groups with a default permission set) through
`saas/core/utils/group_creator.py`, called from their `post_migrate` (e.g.
`saude/apps.py` with `saude/profiles.py`):

```python
report = group_creator([{"name": "Registered Nurse", "permissions": ["view_paciente", "add_dadovital"]}],
                       rename_from={"Registered Nurse": "Enfermeiro"})
```

- **Idempotent and additive.** An existing Group (by name) is reused, never duplicated; `rename_from`
  renames an old name in place (same `id`, relations kept). It accepts one old name or a **list**
  (e.g. `{"Doctor": ["General Practitioner", "Médico Geral"]}`): the first that exists is renamed. Default permissions are **added**; permissions
  an administrator added are never removed.
- **Real codenames only.** A codename that doesn't exist is **not created and not assigned**. It is logged as
  a warning and listed in the returned report (`permissions_missing`). The report also has `groups_created`,
  `groups_reused`, `groups_renamed`, `permissions_assigned` and `permissions_already_assigned` per profile.
- **Ordering.** Permissions a module creates itself (e.g. dashboard permissions) must exist before its
  profiles are seeded: connect that `post_migrate` receiver first.
- Profiles are **global Groups** linked to the EntityType as templates (see *Managing group permissions*):
  changing their permissions is a platform-level operation.

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
     clients cannot set the flag (read-only in `GroupSerializer`). Groups that
     existed before this rule can be marked with `manage.py mark_editable_groups`
     (dry run by default).
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
| `GET {id}/permissions_csv/` | `view_group` | visible group; CSV `app, model, codename, name` (UTF-8 with BOM); cells starting with `= + - @` are prefixed with `'` (no spreadsheet formulas) |
| `GET {id}/permissions_pdf/` | `view_group` | visible group; the generic list PDF (`django_resaas/pdf/list.html`) with the Entity's branding |
| `POST {id}/import_permissions/` (multipart `file`, `mode=add\|replace`) | `change_group` | changeable group (rule 2) + no escalation (rule 3) on every permission added **or removed** |

**CSV import** (`saas/core/services/group_permissions_io_service.py`): a `codename`
column is required; `app` disambiguates a codename that exists in several apps
(e.g. `view_group` in `django_resaas` and `auth`). The file is validated **before**
anything changes. Any unknown or ambiguous row returns `400 invalid_rows` with
`error.details.rows` (`{line: [message]}`), and nothing is applied. `mode=add`
(default) only adds; `replace` makes the group's permissions exactly the file's.
The limits are 1 MB and 5,000 rows, in UTF-8. The answer is
`{mode, added, removed, unchanged, total}`. The change is audited
(`GROUP_PERMISSIONS_IMPORTED`). A file downloaded with `permissions_csv` can be
edited and imported back.

### Legacy viewsets: per-action permissions (`ActionPermissionMixin`)

`ExplicitAccessMixin` only decides who may **reach** a plain `ModelViewSet`
(authenticated, or public for listed safe actions). `ActionPermissionMixin`
(`saas/core/base/access.py`) adds what `BaseAPIView` does: every action needs its
permission in the signed context, and an undeclared action is refused (`403
permission_denied`). Actions listed in `membership_actions` need no permission,
and the view's `get_queryset` must scope them to the caller's own objects.
`is_membership_request()` can decide this per request.

```python
class EntityAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    membership_actions = ("list", "retrieve", "branchs", "apps", "models", "themeGet", ...)
    action_permissions = {"update": "change_entity", "addUser": "add_entityuser", ...}
```

| View | No permission (membership) | Everything else |
|---|---|---|
| `EntityAPIView` (`django_resaas/entitys/`) | the caller's own Entities: list, detail, branches, active apps/models, branding reads; `create` (self-service registration of a **new** Entity) | its permission (`change_entity`, `add_entityuser`, `add_entitygroup`, ...) **and** only on the Entity of the signed context (another one is `404`), unless platform level (`change_entitytype`) |
| `EntityTypeAPIView` (`django_resaas/entitytypes/`) | **the catalogue list (`GET entitytypes/`) is PUBLIC**, read only: live types with `id`, `name`, `label`, `icon`, `ordem` (`EntityTypePublicSerializer`; header services menu, login screen) - every field and deleted types need `list_entitytype`; branding reads (public); the caller's **own** EntityType: detail, apps, models, groups, permissions; `user_entitys` (own Entities only) | reads of other types and cross-tenant lists (`entitys`, `branches_map`) need `view_entitytype`; every write is platform level (`change_entitytype`, `add_/delete_entitytype`) |

**EntityType profiles export / import** (EntityType -> template profiles -> permissions, JSON
because of the nesting; `saas/core/services/entity_type_profiles_io_service.py`, built on the
group functions of `group_permissions_io_service`):

| Action | Permission | Notes |
|---|---|---|
| `GET entitytypes/{id}/profiles_json/` | `view_entitytype` (or the caller's own type) | `{"format": "resaas.entity_type_profiles", "version": 1, "entity_type", "profiles": [{"name", "permissions": [{app, model, codename, name}]}]}` |
| `GET entitytypes/{id}/profiles_pdf/` | `view_entitytype` (or own type) | generic list PDF: profile, app, model, codename, name |
| `POST entitytypes/{id}/import_profiles/` (multipart `file`, `mode=add\|replace`) | `change_entitytype` | see below |

Import: the whole file is validated first (`400 invalid_profiles`, `error.details.profiles`
keyed `profiles[i] <name>`), and nothing changes if any profile is wrong. A profile that
doesn't exist is created and linked as a template of the type. `mode` applies to each
**listed** profile (`add` / `replace` its permissions); profiles not in the file are never
touched. Permissions may be `{"app", "codename"}` or a bare codename (`app` is needed when
the codename exists in several apps). **Refused**: a platform profile (one holding
`change_entitytype`, e.g. Root) and the `change_entitytype` permission itself, because a
template is inherited by every Entity of the type. The group rules also apply to every
profile: no permission added or removed that the caller doesn't hold. Limits: 2 MB, 200
profiles. Audited (`ENTITY_TYPE_PROFILES_IMPORTED`). The answer is
`{mode, created, profiles: [{name, created, added, removed, total}]}`. An exported file
imports back unchanged.

`EntityAPIView.addGroup` only links a group that is a template of the Entity's own
EntityType (`403 group_not_in_entity_type` otherwise, unless platform level).
Linking any group, e.g. Root, would let the Entity's admins assign it through
`users/{id}/addGroup/`.

### Deploy endpoints (`deploy/*`)

**PUBLIC by design** (GitHub webhook / operations), authenticated by a shared
token: header `X-Deploy-Token` (preferred) or `?token=` (kept for existing
webhooks), compared in constant time. There is **no default token**: without
`settings.DEPLOY_TOKEN` every call is refused. `deploy/github/` and
`deploy/rollback/` change the server and are **POST only** (`405` on GET).
`status`, `releases` and `logs` are read-only GETs.

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
