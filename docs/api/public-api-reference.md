# Public API Reference

`django_resaas` is a reusable Django app, not a standalone library with a curated top-level
`__init__.py` export list. Its `__init__.py` files are intentionally empty (eagerly importing
models or views there would risk `AppRegistryNotReady` errors before Django finishes loading
installed apps). The supported, working convention is **deep import** - importing each class
directly from the module that defines it. This page documents that existing surface; it does not
introduce a new one.

## Base classes (`django_resaas.core.base`)

### `BaseModel` - `django_resaas.core.base.models.BaseModel`

The model base class most application models should inherit from. Built in layers:

-   `SoftBaseModel` - adds a UUID primary key, `created_at`/`updated_at`/`deleted_at`, and three
    managers: `objects` (alive rows only), `all_objects` (everything), `deleted_objects`
    (soft-deleted rows only). `delete()` sets `deleted_at` instead of removing the row;
    `hard_delete()` performs the real deletion; `restore()` clears `deleted_at`.
-   `TimeModel` - adds `created_by`/`updated_by` (FK to `AUTH_USER_MODEL`) and a `state`
    (`Active`/`Inactive`) field.
-   `BaseModel` - adds the tenant `entity`/`branch` foreign keys and `ensure_tenant()`, which
    `save()` calls automatically to backfill `entity`/`branch` from the first available record
    when they weren't set explicitly.

Also exported from the same module: `SoftDeleteQuerySet`, `SoftDeleteManager`, `DeletedManager`,
`AllObjectsManager`, and the `file_path(instance, file_name, pasta="")` upload-path helper (builds
`{entity_type_id}/{entity_id}/{instance_id}/{pasta}/{filename}`).

### `BaseSerializer` - `django_resaas.core.base.serializers.BaseSerializer`

The `ModelSerializer` base class, composed from four mixins (`DynamicFieldsMixin`,
`SerializerUtilsMixin`, `FileFieldsMixin`, `RepresentationMixin`). Automatically marks
`DEFAULT_READ_ONLY_FIELDS` (`id`, `entity`, `branch`, `created_by`, `updated_by`, `created_at`,
`updated_at`, `deleted_at`) as read-only on every subclass, so callers don't need to repeat that
list per serializer. `label_field` and `value_field` (default `"id"`) support the framework's
generic label/value representation.

### `BaseAPIView` - `django_resaas.core.base.views.BaseAPIView`

The `ModelViewSet` base class - see [`docs/api/base-api-view.md`](base-api-view.md) for its
responsibilities (CRUD, filters, ordering, search, permissions, multi-tenancy, soft
delete/restore/hard delete). Also in this module:

-   `registerView(name=None, module=None)` - class decorator that registers a view class into the
    global `VIEW_REGISTRY` (`django_resaas.core.base.registry.VIEW_REGISTRY`), keyed by
    `module` (default: the class's top-level package) and `name` (default: the class name,
    lowercased, `APIView` suffix stripped, pluralized with a trailing `s`). This registry is what
    `core.utils.autoload_urls.build_saas_urls()` walks to build the router automatically - see
    [`docs/development/creating-resource.md`](../development/creating-resource.md) for a full
    usage example.

### `HasAppPermission` and friends - `django_resaas.core.base.permissions.py`

-   `HasAppPermission` - a DRF `BasePermission`. Reads `permission_codename` off the view and
    delegates to `check_permission()`.
-   `check_permission(request, role)` - the actual authorization check: requires an authenticated
    user plus a full tenant context on the request (`entity_type_id`, `entity_id`, `branch_id`,
    `group_id`, `lang_id`), then checks in one query whether the user's `BranchUserGroup` grants a
    permission with that `codename` for the current branch/entity/entity_type.
-   `hasApp(codigo)` - method decorator; 403s unless the given app `codigo` is active
    (`EntityApp`, `state=1`) for the request's entity. **Known issue:** it filters on
    `app__codigo`, but `django_resaas.models.app.App` has no `codigo` field - calling this
    decorator would raise `FieldError`. It has zero call sites in the current codebase, so this
    hasn't surfaced; flagging it here rather than fixing it, since fixing would mean guessing at
    the intended field name/semantics (out of scope for a docs-only pass).
-   `hasPermission(role=None)` - method decorator wrapping `check_permission()`, returning a 403
    `fail()` response instead of raising.
-   `isPermited(request=None, role=None)` - a thin alias for `check_permission()`.

## `resaas_action` - `django_resaas.core.decorators.action.resaas_action`

```python
@resaas_action(*, methods=None, detail=False, label=None, icon=None, tooltip=None,
                position=None, order=0, visible=True, autorequest=False,
                url_path=None, url_name=None)
```

Declares a custom action on a `ViewSet`/`BaseAPIView`, layering RESAAS metadata (label, icon,
tooltip, position, order, visibility, whether the frontend should auto-request it) on top of DRF's
own `@action` decorator. The decorated method's name becomes the action name and (unless
overridden) the URL path/name and the permission codename base. The decorator itself does not
write to the database - metadata is stashed on the function as `_resaas_action` and persisted by
`ActionSyncService` (see [`docs/development/management-commands.md`](../development/management-commands.md#sync_actions)),
which is what makes the action show up in `ResaasSchemaBuilder`'s `actions`/`permissions.custom`
output (see [`docs/api/schema-contract.md`](schema-contract.md)).

## `ResaasSchemaBuilder` - `django_resaas.core.schema.ResaasSchemaBuilder`

```python
from django_resaas.core.schema import ResaasSchemaBuilder
```

Turns a model into the versioned "Schema 1.0" JSON contract consumed by frontends. Its exact
output shape, versioning policy, and merge semantics are documented separately in
[`docs/api/schema-contract.md`](schema-contract.md) - this entry exists only to point at the
correct import path.

## `django_resaas.models`

`src/django_resaas/models/__init__.py` re-exports a small, specific subset of the ~25 models in
that package:

```python
from django_resaas.models import Document, Person, EntityTypeGroup, CorsAllowedOrigin, ModelExtraAction
```

Every other model is imported from its own module - e.g.:

```python
from django_resaas.models.user import User
from django_resaas.models.group import Group
from django_resaas.models.entity import Entity
from django_resaas.models.branch import Branch
```

There is no documented rule for why those five are re-exported and the rest aren't; treat it as
existing behavior to preserve; don't rely on more models being added to that list without
checking `models/__init__.py` first.
