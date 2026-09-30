# Upgrading

## HR is no longer part of `django_resaas` (breaking change)

`django_resaas.hr` has been removed from the package. HR is business domain,
not framework: it now lives in the application that uses it, as that
application's own `hr` module. The framework starts, migrates and passes its
tests with no business module installed.

There is **no compatibility import** `django_resaas.hr`: the framework cannot
depend on an application's code.

An application that used `django_resaas.hr`:

1. **Takes the module's code** into the project as an app named `hr` (the
   last `django_resaas` release that shipped it has it under
   `django_resaas/hr/`), and rewrites its imports from `django_resaas.hr...`
   to `hr...`, e.g. `sed -i 's/django_resaas\.hr\b/hr/g'`. Its `AppConfig`
   keeps `label = "hr"`, so tables, ContentTypes, permissions and
   `'hr.Employee'` references stay exactly the same, with no data migration.
2. **Settings:** `'django_resaas.hr'` → `'hr'` in `MY_APPS`, and
   `RESAAS_DEFAULT_MODULES = ["hr"]` to keep activating it for new
   EntityTypes (the framework used to do it by default).
3. **Its own imports** elsewhere: `from django_resaas.hr...` → `from hr...`.
4. **Migrations:** the module's `0001_initial` keeps its name. Apply the
   shipped-migrations upgrade below.

What moved with it, so that the core names no business module:

| Before (in the core) | Now |
|---|---|
| `include('django_resaas.hr.urls')` in `django_resaas/urls.py` | nothing: the module's views are `@registerView(..., module="hr")`, served by `build_saas_urls()` |
| HR dashboard permissions in the core's `MODULE_PERMISSIONS` | the module's `apps.py`, via the public `ensure_module_permissions()` |
| `view_employee`, `view_department`, ... in the core's administration profiles | the module's `profiles.py` (added to the same profiles by name) |
| `hr` activated for every new EntityType | `settings.RESAAS_DEFAULT_MODULES` |
| `hr` reserved/protected in the scaffold | only the framework's own apps are |

The tenant test fixtures the framework used internally are now public:
`django_resaas.testing` (see [Building a module](../development/building-a-module.md)).

## Framework migrations are shipped with the package

`django_resaas` ships its own migrations, one `0001_initial` per framework app
(`django_resaas`, `notifications`), in `src/django_resaas/*/migrations/`.
A new installation just runs `migrate`.

Up to **0.0.621** they were not versioned. Every environment generated its own
with `makemigrations`, inside the installed package (the virtualenv), so each
environment ended up with a different history for the same schema. For example,
one environment had `django_resaas` 0001–0007 and another had 0001–0003.

That was fragile in two ways:

- a reinstall of the package (`pip install --force-reinstall`) deleted those
  files;
- a project's own migrations could depend on names that exist only in that one
  environment, such as `('django_resaas', '0003_entity_founded_on_...')`.

Your own apps' migrations (`saude`, `sales`, ...) are unaffected: they depend on
`("django_resaas", "0001_initial")` (and `("hr", "0001_initial")`, now the
application's own module - same name), which still exist
under the same name.

The shipped `0001_initial` has **the same schema** as the old histories. This
was checked by building a database from the shipped migrations and comparing
it with two environments that had different histories. The tables, columns,
types, indexes and constraints matched. The only difference is the name of the
`username` unique constraint (`..._key` vs `..._uniq`), which Django resolves
by introspection.

### Upgrading an environment created before

Do this once per environment (dev, staging, production), in this order:

```bash
# 0. the database is fully migrated with the version you are leaving
python manage.py migrate

# 1. backup
pg_dump ... > before-rebaseline.dump

# 2. install the new django_resaas (it brings its migrations)
pip install -U django_resaas

# 3. see what will change - dry run, changes nothing
python manage.py resaas_migrations_rebaseline

# 4. apply
python manage.py resaas_migrations_rebaseline --apply

# 5. verify
python manage.py migrate                        # "No migrations to apply."
python manage.py makemigrations --check --dry-run   # "No changes detected"
```

`resaas_migrations_rebaseline` does two things, and prints them first:

- **Repoints project migrations.** A migration of one of your apps that depends
  on a framework migration which no longer exists is pointed at the latest
  migration the framework ships (same schema). Only files under `BASE_DIR` are
  touched, never an installed package.
- **Prunes stale rows.** Rows of `django_migrations` for framework migrations
  that no longer exist are deleted. Otherwise, a future shipped migration with
  the same name as an old local one would be considered applied without ever
  running.

It is idempotent: a second run reports nothing to do. It never changes the
schema or any data.

### Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `NodeNotFoundError: ... dependencies reference nonexistent parent node ('django_resaas', '000X_...')` | Step 4 has not run yet: run `resaas_migrations_rebaseline --apply` |
| `makemigrations --check` reports changes in `django_resaas`/`notifications` after the upgrade | The database was not fully migrated with the previous version (step 0), or the project runs an older package: stop, restore the backup, redo from step 0 |
| `makemigrations` creates files inside the installed package | Never commit or keep those. The framework's migrations come from the package. Report the model change upstream |

## Framework developers: model changes need a migration

Changing a model of the framework now means shipping its migration:

```bash
cd src
python3 manage.py makemigrations django_resaas notifications
```

`saas/tests/test_shipped_migrations.py` fails when a model changed without its
migration.
