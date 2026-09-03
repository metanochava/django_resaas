# Management Commands

## `create_root`

```bash
python manage.py create_root
```

The full enterprise bootstrap command. Interactively prompts for a username/email (rejecting an
already-used email) and a password (hidden input, with confirmation), then creates a superuser and
the complete default tenant structure in one pass: an `EntityType` ("SaaS"), an `Entity`
("Tenant"), a `Branch` ("Main"), the default `GROUPS` (Guest, Admin, Root) linked to the entity
type/entity/branch/user, the `django_resaas` and `hr` apps registered and linked to the entity
type/entity, plus frontend and language defaults (via `FrontEndService.load_defaults` and
`LanguageService.load_defaults`). Intended to be run once per environment to get a fully working
system from a blank database.

## `create_entity`

```bash
python manage.py create_entity
```

A lighter, interactive bootstrap: prompts for an entity type name, entity name and branch name,
gets or creates a superuser via `UserService.get_or_create_superuser`, then delegates the actual
entity/branch/group wiring to `BootstrapService.run(...)`. Use this when you need another
entity/branch under an existing setup rather than the full from-scratch `create_root` flow.

## `sync_actions`

```bash
python manage.py sync_actions
```

Synchronizes `@resaas_action`-decorated methods with `ModelExtraAction` rows and Django
`Permission` objects. Reads every view registered in `VIEW_REGISTRY` (see
[`docs/api/public-api-reference.md`](../api/public-api-reference.md) for how views get registered
via `registerView`), prints each module and view found, then calls
`ActionSyncService.sync_registry(VIEW_REGISTRY)` inside a transaction. Run this after adding or
changing `@resaas_action` methods so their metadata (label, icon, permission, endpoint) becomes
visible through `ResaasSchemaBuilder`'s `actions`/`permissions.custom` output. Warns and exits
early if `VIEW_REGISTRY` is empty (no views were registered/imported yet).

## `sync_language`

```bash
python manage.py sync_language
```

Loads the default languages by calling `TranslationSyncService.sync(...)`.

## `setup`

```bash
python manage.py setup
```

Loads system defaults in sequence: `LanguageService.load_defaults(...)`,
`FrontEndService.load_defaults(...)`, `TranslationService.load_defaults(...)`. A narrower bootstrap
than `create_root`/`create_entity` - it does not create a superuser or tenant structure, only the
language/frontend/translation baseline data.

## `check` (Django's real system check)

```bash
python manage.py check
```

> [!NOTE]
> As of the Phase 2 cleanup, this runs Django's own system check framework
> (`django.core.checks`). Previously, a project-local command was shadowing it under the
> same name — see `check_metano` below for where that renamed to.

## `check_metano`

```bash
python manage.py check_metano [--path PATH] [--strict]
```

The project-local "MetanoStack compliance" linter (was `check.py`, renamed in Phase 2 because it
was shadowing Django's built-in `check` command above). Recursively scans `.py` files under
`--path` (default `.`) for a small set of forbidden textual patterns: `models.Model`,
`ModelSerializer`, `ModelViewSet`, and `from .` (relative imports) - the idea being that
application code should build on the framework's `BaseModel`/`BaseSerializer`/`BaseAPIView` and use
absolute imports rather than Django's raw base classes or relative imports. Prints one line per
match found; with `--strict`, raises `CommandError` (non-zero exit) if any match is found,
otherwise it only reports and returns normally - useful for CI vs. local advisory use respectively.
