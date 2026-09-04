# Management Commands

## The RESAAS operational layer: `resaas_setup` / `resaas_sync` / `resaas_doctor`

Three official entry points, each backed by reusable services/checks rather than logic living
inside the command itself, so the same behaviour is available to tests/CI/scripts without going
through `call_command`:

- **`resaas_setup`** prepares (bootstrap) - global baseline data.
- **`resaas_sync`** reconciles - code-declared metadata -> persisted metadata.
- **`resaas_doctor`** diagnoses - read-only, safe in production/CI.

```bash
python manage.py resaas_setup

python manage.py resaas_sync
python manage.py resaas_sync --dry-run
python manage.py resaas_sync --only actions -v 2

python manage.py resaas_doctor
python manage.py resaas_doctor --json
python manage.py resaas_doctor --check database --check migrations
python manage.py resaas_doctor --fail-on-warning

python manage.py resaas_check          # alias of resaas_doctor
python manage.py resaas_schema_check   # equivalent to `resaas_doctor --check schema`
```

### `resaas_setup`

Prepares the global baseline metadata a RESAAS installation needs: languages, frontend defaults,
translations - the exact same three calls `setup` (below) already made
(`LanguageService.load_defaults`, `FrontEndService.load_defaults`,
`TranslationService.load_defaults`), now living in a shared `run_setup()` function in
`resaas_setup.py` that `setup` delegates to, so the two commands can never drift apart.
Idempotent (every service underneath uses `get_or_create`). Deliberately does **not** create a
superuser or any tenant structure - use `create_entity`/`create_root` for that.

### `resaas_sync`

Reconciles code-declared RESAAS metadata with what's persisted in the database. Today that means
one thing: `@resaas_action` -> `ModelExtraAction`/`Permission`, via `ActionSyncService` - the exact
same service `sync_actions` (below) and the `post_migrate` signal in
`core/signals/action_sync.py` already use, so there is exactly one place this logic lives.

Permissions and Groups are **not** duplicated here - they already sync automatically on every
`manage.py migrate` (see `core/signals/permissions.py` and `apps.py`). `resaas_sync` only exists
for reconciling code-level metadata without running migrations (e.g. you added a
`@resaas_action` but didn't touch any model).

`--dry-run` computes what would change - created/updated/deleted/unchanged counts - without
writing anything: internally it runs the exact same code path inside a transaction that is always
rolled back via `transaction.set_rollback(True)`, rather than a second, hand-written "simulate"
implementation that could drift from the real one. `--only actions` limits which targets sync (the
only target today; the flag exists so more can be added later without a breaking CLI change).
`-v 0..3` controls verbosity the normal Django way - `-v 2` also lists every individual
created/updated/deleted action identity.

Running it twice in a row is idempotent: the second run reports everything as "Unchanged" and
creates no duplicate rows (`ModelExtraAction` enforces this at the DB level too, via a unique
constraint on `(app, model, action)`).

### `resaas_doctor` / `resaas_check`

Structural diagnostic: database connectivity, pending migrations, `VIEW_REGISTRY` sanity,
`@resaas_action` sync drift (via `ActionSyncService.sync_registry(..., dry_run=True)`), the
`ResaasSchemaBuilder` contract for every model behind a registered view, expected model
permissions, and `EntityTypeApp`/`App` structural consistency. **Never writes to the database** -
read-only checks plus the same write+rollback trick `--dry-run` uses for the actions check, so
nothing is ever actually persisted.

Each check lives in `core/doctor/checks.py` as a small, independent `Check` subclass registered
into `core/doctor/base.CHECK_REGISTRY` via a `@register_check` decorator - the same
dict-plus-decorator shape `VIEW_REGISTRY`/`registerView` already uses for views. Any app
(`notifications`, `hr`, `sales`, ...) can contribute a check by importing `core.doctor.base` and
decorating a `Check` subclass; `resaas_doctor` never needs to know about them ahead of time.

`resaas_check` is a real alias (a subclass, not a copy-pasted file) - the original design asked for
both names with slightly different framing ("check" for structural validation, "doctor" for the
broader diagnostic), but once every check lived in one registry there was no actual behavioural
split left to preserve.

Flags: `--json` (machine-readable output only - never mixed with human-formatted text),
`--check NAME` (repeatable, limits which checks run; unknown names raise `CommandError`),
`--fail-on-warning` (exit code 1 when only warnings were found; an error always exits 2 regardless
of this flag; a clean run exits 0).

A **warning** you will legitimately see on a healthy install is an unsynced `@resaas_action` (run
`resaas_sync`) or a missing model permission (run `migrate`, which creates them via the
`post_migrate` signal). A registered view with no resolvable model (dashboards, the scaffold
endpoint, the notification catalog, ...) is reported at **info**, not warning - that's a normal,
valid shape of view in this codebase, not a defect.

### `resaas_schema_check`

Validates the RESAAS Schema 1.0 contract (`ResaasSchemaBuilder.build()`) for every model behind a
registered view - no HTTP, no business data, just the structural contract the `quasar_resaas`
frontend relies on (`schema.model.endpoint`). Equivalent to `resaas_doctor --check schema`; kept as
its own command because schema validation is a common enough single thing to want in a CI step on
its own. `--json` for machine-readable output; exits 2 if any model's schema fails to build.

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
`ActionSyncService.sync_registry(VIEW_REGISTRY)` (which manages its own transaction). Run this
after adding or changing `@resaas_action` methods so their metadata (label, icon, permission,
endpoint) becomes visible through `ResaasSchemaBuilder`'s `actions`/`permissions.custom` output.
Warns and exits early if `VIEW_REGISTRY` is empty (no views were registered/imported yet).

> [!NOTE]
> Kept as a permanent, fully-supported alias - see `resaas_sync` above, which hits the exact same
> `ActionSyncService.sync_registry` call and additionally supports `--dry-run`/`--only`/`-v`.

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

> [!NOTE]
> Kept as a permanent, fully-supported alias - see `resaas_setup` above, which delegates to the
> same `run_setup()` function this command now calls.

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
