# The RESAAS Schema Contract (v1.0)

`ResaasSchemaBuilder` (`django_resaas.core.schema.ResaasSchemaBuilder`) turns a Django model into
a declarative JSON contract that a frontend (`quasar_resaas` in particular) consumes to render a
full CRUD screen — table, form, filters, pagination, permissions, actions, PDF export — without
hardcoding any of those conventions on the client.

It is served by `AppSchemaAPIView` (`management/apicommands/view/app_schema.py`) at the app's
`.../<app>/<model>/schema/` endpoint, and is exercised end-to-end by the demo app in
[`src/dev/demo`](../../src/dev/README.md).

This document is the authoritative reference for that shape. It is protected by
`src/django_resaas/core/schema/tests/test_builder.py` — any change to the JSON below must come
with a matching test change, so drift between this doc and the real output is caught in CI.

## Usage

```python
from django_resaas.core.schema import ResaasSchemaBuilder

schema = ResaasSchemaBuilder(Model=SomeModel, fields=serialized_field_list).build()
```

`fields` is the list of field descriptors the caller already derived from the model's serializer
(each at minimum `{"name": "<field_name>"}`); the builder does not introspect serializers itself.

## Versioning policy

- `schema_version` is currently frozen at `"1.0"`.
- **Additive, backward-compatible changes** (a new key, a new optional field on an existing
  object) do not require a version bump.
- **Breaking changes** (removing/renaming a key, changing a field's type or meaning) require
  bumping `ResaasSchemaBuilder.SCHEMA_VERSION` to `"2.0"`. Consumers should check `schema_version`
  before relying on 2.0-only behavior.
- `module` and `config` (see below) are **deprecated aliases** kept only for backward
  compatibility with older consumers. New code should read `model.app` and `routes`/`ui.crud`
  directly instead.

## Shape

```jsonc
{
  "schema_version": "1.0",

  "model": {
    "app": "django_resaas",         // Model._meta.app_label
    "name": "group",                // Model._meta.model_name
    "class_name": "Group",          // Model.__name__
    "label": "Group",               // Model._meta.verbose_name, titlecased
    "label_plural": "Groups",       // Model._meta.verbose_name_plural, titlecased
    "pk": "id",                     // Model._meta.pk.name
    "endpoint": "django_resaas/groups/"  // "{app}/{model}s/" convention
  },

  "fields": [ /* the `fields` list passed in, unmodified */ ],

  "actions": [
    {
      "action": "archive",
      "app": "django_resaas",
      "model": "group",
      "label": "Archive",
      "icon": null,
      "tooltip": null,
      "position": null,
      "order": 0,
      "visible": true,
      "method": "POST",               // the single method the UI should submit this action with - always one value, never comma-joined
      "methods": ["POST"],            // every HTTP method DRF actually routes to the handler (from `@resaas_action(methods=[...])`); "method" above is always methods[0]
      "detail": true,                // conceptual/API name (matches DRF's own `detail=`) - always equal to "details"
      "details": true,               // kept for backward compatibility with existing frontend code; detail action -> ".../{id}/archive/"
      "url": null,
      "autorequest": false,
      "endpoint": "django_resaas/groups/{id}/archive/",
      "permission": "archive_group"
    }
    // one entry per ModelExtraAction row for this app+model,
    // ordered by (order, action)
  ],

  "permissions": {
    "list": "list_group", "view": "view_group", "add": "add_group",
    "change": "change_group", "delete": "delete_group",
    "restore": "restore_group", "hard_delete": "hard_delete_group",
    "pdf": "pdf_group", "pdf_list": "pdf_list_group",
    "custom": { "archive": "archive_group" }   // one entry per ModelExtraAction
  },

  "routes": {
    // convention defaults ("{verb}_{model}"), overridable per-key via
    // `RESAAS.routes` (a dict merge, not a wholesale replacement)
    "list": "list_group", "add": "add_group",
    "change": "change_group", "view": "view_group"
  },

  "ui": {
    "title": "Groups",              // verbose_name_plural, titlecased
    "icon": null,                   // RESAAS.icon
    "crud": true,                   // RESAAS.crud, default true
    "dense": true, "striped": true,
    "show_search": true, "show_filters": true, "show_columns": true,
    "show_refresh": true, "show_pdf": true, "show_pdf_list": true
    // any key above overridable via `RESAAS.ui = {...}` (merged over defaults)
  },

  "filters": {
    "enabled": true,
    "search": true,
    "search_fields": [],            // RESAAS.search_fields
    "fields": ["name", "editable"]  // names pulled from the `fields` argument
    // overridable via `RESAAS.filters = {...}` (merged over defaults)
  },

  "pagination": {
    "enabled": true,
    "page_size": 10,                // from REST_FRAMEWORK["PAGE_SIZE"], default 10
    "page_size_options": [5, 10, 20, 50, 100, 200, 500, 1000, 0],
    "default_ordering": "-id"
    // overridable via `RESAAS.pagination = {...}` (merged over defaults)
  },

  "pdf": {
    "enabled": true, "detail": true, "list": true,
    "detail_permission": "pdf_group", "list_permission": "pdf_list_group",
    "detail_endpoint": "django_resaas/groups/{id}/pdf/",
    "list_endpoint": "django_resaas/groups/pdflist/"
    // overridable via `RESAAS.pdf = {...}` (merged over defaults)
  },

  // --- deprecated backward-compatibility aliases, see Versioning above ---
  "module": "django_resaas",        // duplicate of model.app
  "config": {
    "crud": true,                   // duplicate of ui.crud
    "routes": { /* duplicate of routes */ }
  }
}
```

## Merge semantics

Every overridable section (`ui`, `filters`, `pagination`, `pdf`, `routes`) is a **shallow dict
merge**: `{**default, **(configured or {})}`. Supplying `RESAAS.ui = {"dense": False}` only
overrides `dense` — every other `ui` key keeps its default. This is why a consumer should never
re-declare these defaults locally (see [`docs/api/public-api-reference.md`](public-api-reference.md)
and the frontend's `quasar_resaas` `utils/schema.js`, which now imports these constants instead of
re-declaring them) — the backend is the single source of truth for what "unset" means.

## Related

- [`docs/models/resaas-config.md`](../models/resaas-config.md) — the `class RESAAS` convention on
  the model side (`label_field`, `search_fields`, `crud`, and the sections documented above).
- `src/django_resaas/core/schema/tests/test_builder.py` — the executable version of this contract.
