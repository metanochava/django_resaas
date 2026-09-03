# Backend Troubleshooting

## `RESAAS context is required.` (403)

`initial()` rejects any request with no decoded `request.tenant_context` at all. Check:

1. The `X-RESAAS-Context` header is actually being sent.
2. The token was issued by `POST /api/resaas/context/` and hasn't expired.
3. `ResaasContextService.decode(token)` isn't failing silently — a decode failure lands in
   `request.tenant_context_error` and raises its own, more specific `PermissionDenied` before this
   one does. See [Multi-tenancy](../architecture/multi-tenancy.md).

## `Module '<name>' is not active.` (403)

The app is installed and its view is registered, but the tenant hasn't activated it:

```python
from django_resaas.models.app import App
from django_resaas.models.entity_app import EntityApp

app, _ = App.objects.get_or_create(name="<name>", defaults={"state": "Active"})
EntityApp.objects.get_or_create(entity=my_entity, app=app, defaults={"state": "Active"})
```

See [BaseAPIView#module-activation](../api/base-api-view.md#module-activation). Activation is
per-entity — activating for one tenant never activates it for another.

## `Module '<name>' is not defined.` (403)

The view has no `module_name` set at all — it was never decorated with `@register_view(...)` /
`@registerView(...)`, or the decorator was applied without importing this module before
`build_saas_urls()` runs. See
[View registry#when-view_registry-is-actually-populated](../architecture/registry.md#when-view_registry-is-actually-populated).

## `Unauthorized` (403) on an action that should be allowed

1. Confirm the expected codename actually exists:
   `Permission.objects.filter(content_type__model="<model>", codename="<prefix>_<model>")`.
2. Confirm the user's group has it, for the *current* branch — `check_permission()` resolves
   permissions per branch/entity/entity_type, not globally. See [Permissions](../security/permissions.md).
3. > [!TIP]
   > The per-request permission cache (`request._perm_cache`) only lives for that one
   > request — granting a permission takes effect on the next request, not retroactively.

## `django.core.exceptions.ValidationError` on save, mentioning "explicit entity and branch"

A `BaseModel` instance was saved without `entity`/`branch` set, outside the API (shell,
management command, signal, migration, fixture). This is intentional —
`BaseModel.ensure_tenant()` never guesses a tenant. Set both explicitly before saving. See
[Multi-tenancy#golden-rule-the-tenant-is-never-guessed](../architecture/multi-tenancy.md#golden-rule-the-tenant-is-never-guessed).

## Search returns every record, or none

1. Confirm `search` is actually arriving in `request.query_params` (a typo'd param name, e.g.
   `?q=` instead of `?search=`, is silently ignored — an empty search is a no-op, not an error).
2. If `RESAAS.search_fields` is declared, confirm the field names are spelled correctly — an
   invalid entry is silently skipped rather than raising, so a typo just quietly narrows what's
   searched. See [Search](../api/search.md).
3. Without `search_fields`, only direct `Char`/`Text`/`Email` fields on the model itself are
   searched — a relation won't match unless `search_fields` is declared explicitly.
4. Inspect the actual SQL with `print(qs.query)` if the above doesn't explain it.

## `ImproperlyConfigured` from `sync_actions` / `post_migrate`

A `@resaas_action` was declared with the same `app`/`model`/`action` identity as an existing
`ModelExtraAction` row whose `managed_by` is `"manual"`. The sync refuses to silently take over a
manually-created row. Either rename the action, or set `managed_by="decorator"` on the existing
row yourself first if handing it to the decorator is intentional. See
[Permissions#custom-action-permissions-and-ownership](../security/permissions.md#custom-action-permissions-and-ownership).

## `Fatal: There is an existing release branch`

Resolve or delete the existing `release/x.y.z` branch before starting another one — see
[Git flow and releases](../deployment/releases.md#before-starting-a-release).
