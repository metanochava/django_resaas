# Upgrading

## Person filiation, POST status codes (next release after 0.0.632)

| Change | Kind | What to do |
|---|---|---|
| `Person.father_name` and `Person.mother_name` (optional text, max 150): the parents' names as on identity documents. Shipped migration `django_resaas.0002_person_father_name_person_mother_name`; the Person API and schema expose them; quasar_resaas shows them in the personal data (`PersonIntakeSections`, `PersonProfilePanel`) | Backward compatible (new nullable columns) | `python manage.py migrate` |
| A successful `POST` answers `201` (created), `202` (an operation with a result) or `204` (nothing to return) - never `200`; `ResaasResponseMixin` does it centrally. See [Errors and alerts](../api/errors-and-alerts.md#success-status-codes) | **Behaviour change** for a client that compared a POST answer with `200` | Accept any 2xx (axios already does) |
| Every user holds the **Guest** profile in each Branch they belong to (signal on `BranchUser`); see [Permissions](../security/permissions.md#the-guest-profile-every-member-holds-it) | Backward compatible (one more profile per membership; the login still opens the user's only working profile) | Once per environment: `python manage.py resaas_ensure_guest_profile --apply` |
| `setGroupPermissions` also takes a delta `{group, add, remove}` that never removes an unlisted permission. See [Permissions](../security/permissions.md) | Backward compatible (the full list mode stays) | Prefer the delta in new clients |

## Entitlements, HR translations, packaging (next release after 0.0.624)

| Change | Kind | What to do |
|---|---|---|
| Entitlements (`saas/core/entitlements`, `GET /api/resaas/entitlements/`) | Backward compatible | Nothing: without `RESAAS_ENTITLEMENTS` nothing is restricted. See [Entitlements](../security/entitlements.md). |
| `BaseAPIView`, menus, dashboards and notification rules also ask `has_module()` | Backward compatible | Nothing unless you configure `RESAAS_ENTITLEMENTS["modules"]` or a provider |
| The HR translation keys (`Employee Salary`, `Payroll Item`, `Leave Calendar`, `Add employee`, the HR dashboards' Portuguese labels, ...) left `django_resaas/saas/lang/*.py` | **Breaking** for an application that uses those strings **without** its own HR module | Add them to your HR module's `lang/<code>.py` (the reference application's `hr/lang/` has all four languages) |
| `ResaasAPIException.translate_details`; numbers/booleans in `error.details` are no longer turned into strings | Backward compatible (a client that parsed `"3"` also accepts `3` in JS) | Nothing |
| **List PDF renamed** (bug fix + **breaking**): the base action is now the function `pdf_list` at `GET .../pdf_list/` (was `pdflist` at `.../pdflist/`, which now answers 404), protected by `pdf_list_<model>` — what the schema publishes and the frontend checks — instead of `pdflist_<model>` (users saw the button and got 403). The hooks are `get_pdf_list_context()` / `get_pdf_list_template()` and the attribute `pdf_list_template` | Clients that call the URL by hand: use `.../pdf_list/` (the schema's `pdf.list_endpoint` and quasar_resaas already do). A view that overrides `get_pdflist_context()`/`get_pdflist_template()` or sets `pdflist_template` keeps working with a `DeprecationWarning` — rename them. The action sync drops the old `pdflist` action and its `pdflist_<model>` permissions on the next `migrate`/`resaas_sync`; a group that held only `pdflist_<model>` needs `pdf_list_<model>` (in dev and pro every such group already holds it) |
| **Deploy endpoints removed** (breaking): `django_resaas.view` keeps only `home`; the framework no longer routes `deploy/github`, `status`, `releases`, `logs`, `rollback` (status/logs answered anonymous callers when `DEPLOY_TOKEN` was unset) | An application that imports `deploy`/`deploy_*` from `django_resaas.view` in its own `urls.py` must drop that import and route; deploying belongs to each installation's own tooling |
| The scaffold writes `@register_view` (`registerView` stays a supported alias) | Backward compatible | Nothing |
| The deprecated `dotenv==0.9.9` shim was removed from the dependencies (it shipped no code; `python-dotenv` stays) | Backward compatible | Nothing |
| The wheel no longer ships the framework's tests (they need the repository's `src/dev`) | Backward compatible | Run the tests from a checkout |

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

# 2b. move away the migrations this environment generated inside the package:
#     pip only removes the files it installed, so the old local ones stay next
#     to the shipped ones (two leaf nodes: "Conflicting migrations detected").
#     Keep only what the package ships (its RECORD lists them).
SITE=$(python -c "import django_resaas, os; print(os.path.dirname(django_resaas.__file__))")
mkdir -p backups/stale-framework-migrations
for f in "$SITE"/saas/migrations/0*.py "$SITE"/notifications/migrations/0*.py; do
  grep -q "${f#$SITE/}" "$SITE"/../django_resaas-*.dist-info/RECORD || mv "$f" backups/stale-framework-migrations/
done

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
  on a framework migration which no longer exists is pointed at the newest
  migration the framework ships **that is already applied** - `0001_initial` on
  an environment created before (same schema). A shipped migration that is not
  applied yet (e.g. a `0002` that came with the new package) is never the
  target: `migrate` would refuse the history (`InconsistentMigrationHistory`). Only files under `BASE_DIR` are
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
| `InconsistentMigrationHistory: Migration <app>.000X is applied before its dependency django_resaas.0002_...` | A project migration was pointed at a shipped migration not applied yet (`resaas_migrations_rebaseline` before 0.0.635 did that when the package shipped more than `0001_initial`): point that dependency at `("django_resaas", "0001_initial")` |
| `Conflicting migrations detected; multiple leaf nodes ... (0002_<shipped>, 000X_<local> in django_resaas)` | The environment's own old framework migrations are still inside the installed package: do step 2b, then steps 3-5 |
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
