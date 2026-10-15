# Upgrading

## Person filiation, POST status codes (next release after 0.0.632)

| Change | Kind | What to do |
|---|---|---|
| **Schema endpoints follow the registered view**: `model.endpoint` (and the action / PDF endpoints) use the name a view was registered with (`@register_view("journalentries")`) when the model declares no `RESAAS.endpoint` - before they used `"{model}s"` and pointed at URLs that answer 404 (23 models in the reference application, e.g. `accounting/journalentries`, `inventory/batches`, `sales/taxes`). See [Schema contract](../api/schema-contract.md) | Bug fix (backward compatible: explicit `RESAAS.endpoint` and unnamed views unchanged) | Nothing |
| **Theme ownership** (migration `django_resaas.0007_theme_owner`): a theme without owner is a template; `POST themes/{id}/customize/` copies one for an EntityType, Entity or User and applies it; themes are listed only where visible (templates, own, the context Entity's and its type's); writes follow the owner (`change_theme` for templates, `change_entitytype`, `change_entity` in that Entity, or the owning user). See [Themes](../features/themes.md) | **Breaking**: before, any signed-in user could create/change/delete any theme; now only `change_theme` (Root) changes templates | `python manage.py migrate`; non-Root profiles customize a copy instead of editing templates |
| **Branded e-mails**: every framework e-mail (codes, reset link, welcomes) wears the Entity / EntityType name, logo and Theme colours - `render_email_template(..., request=/entity=)` fills `brand_color`, `brand_text_color`, `brand_tint`, `entity_name`, `logo` from `email_brand()`; the Origin → Entity match now works (it compared `Entity.site` without its scheme and read a non-existent `Entity.display_logo_login`, so no logo was ever shown). See [Transactional e-mails](../features/emails.md) | Backward compatible (`render_email_template(key, context)` unchanged; caller values win) | A custom e-mail template can use the `brand_*` keys |
| **Password reset by e-mail or phone, with a link or a code**: new PUBLIC `POST password/reset/request/` (`channel`, `identifier`, `method`) and `POST password/reset/otp/complete/`; codes bound to their purpose; reset links built only on a trusted origin (CORS policy / `FRONTEND_URL`) and on the real route `/#/auth/resetpassword/…` (also for the legacy `password/reset/email/`); `password/reset/complete/` applies the password policy; `password/change/mobile/` deprecated. See [Password reset](../security/password-reset.md) | **Behaviour change**: a reset link from an origin outside the CORS policy answers `503 reset_link_unavailable`; a weak new password is refused (`400`) | Make sure the frontend origins are in `CORS_ALLOWED_ORIGINS`/`CORS_ALLOWED_ORIGIN_REGEXES` (or set `FRONTEND_URL`); configure an SMS provider for phone resets |
| **`create_root` reuses the platform Entity**: it takes the oldest Entity of the `SaaS` EntityType and creates one ("Tenant") only when none exists. 0.0.652 read `entity.name` from an Entity that a new installation does not have yet (`AttributeError`, no Root could be created); fixed. The unrouted `TenantAPIView` (`saas/data/bootstrap`) follows the same rule, uses the `SaaS` type (it created a separate "Saas" one), answers `POST` instead of a state-changing `GET`, and no longer fails (`NameError` on `entity_type`, `state` on `Group`, the response call). See [Management commands](../development/management-commands.md#create_root) | Bug fix | Nothing |
| **`group_creator` finds the platform Entity by its type**: the profiles are linked to the oldest Entity of the `SaaS` EntityType (no longer an Entity named "Tenant", which it created). 0.0.652 called `Entity.objects.get(..., defaults=...)` and every `migrate` failed in `post_migrate` (`FieldError: Cannot resolve keyword 'defaults'`); fixed. Without a platform Entity (a new installation before `create_root`) the profiles are still created. See [Building a module](../development/building-a-module.md) | Bug fix | Nothing |
| **Entity type sites**: the public page at the root of a type's host. Its content is code of the frontend application (quasar_resaas `registerEntityTypeSiteContent`), its pt/es/fr translations live in `saas/lang/*.py`, its colours in the type's Theme (`manage.py load_entity_type_themes`). `EntityType.site` and `load_entity_type_sites`, added and removed within this release (migrations `django_resaas.0006_entity_type_site` and `0008_remove_entity_type_site`), never reach an installation. See [Public sites](../features/public-sites.md#entity-type-sites) | Backward compatible | `python manage.py migrate`; optionally `python manage.py load_entity_type_themes data/entity_type_themes.json`. An installation that ran the dev build: the `Translation` rows that `load_entity_type_sites` created may be deleted (the static files carry the same texts) |
| `Person.father_name` and `Person.mother_name` (optional text, max 150): the parents' names as on identity documents. Shipped migration `django_resaas.0002_person_father_name_person_mother_name`; the Person API and schema expose them; quasar_resaas shows them in the personal data (`PersonIntakeSections`, `PersonProfilePanel`) | Backward compatible (new nullable columns) | `python manage.py migrate` |
| A successful `POST` answers `201` (created), `202` (an operation with a result) or `204` (nothing to return) - never `200`; `ResaasResponseMixin` does it centrally. See [Errors and alerts](../api/errors-and-alerts.md#success-status-codes) | **Behaviour change** for a client that compared a POST answer with `200` | Accept any 2xx (axios already does) |
| `group_creator()` profiles accept an optional `revoke` list (explicit removal; granting stays additive) and the report has `permissions_revoked`. See [Permissions](../security/permissions.md#profile-templates-group_creator) | Backward compatible (profiles without `revoke` behave as before) | Nothing; a module that revokes applies it on its next `migrate` |
| `AuditLog.details` (JSON, optional) and `audit_service.record(..., details=)`: the facts of an event (a reason, the state it moved from/to). Shipped migration `django_resaas.0003_auditlog_details`. See [Overview](../architecture/overview.md) | Backward compatible (new nullable column; `details` is a keyword with default `None`) | `python manage.py migrate` |
| **Google reviews on public sites**: `Entity.google_place_id` and the PUBLIC `GET site/reviews/` (Google Places API, server key `RESAAS_GOOGLE_PLACES_API_KEY`, cached). Shipped migration `django_resaas.0005_entity_google_place_id`. See [Public sites](../features/public-sites.md#get-sitereviews--the-google-reviews-of-the-sites-place) | Backward compatible: without a key or place there are no reviews | `python manage.py migrate`; set `GOOGLE_PLACES_API_KEY` and the Entity's Google Place ID to show them |
| **Media file tokens are bound to their file**: a token is signed over the URL path it was issued for (a permanent token opened every file before); `FileAccessMiddleware` answers `401` in the error contract (`file_token_invalid`) instead of `{"alert_error"}`; new `FILE_TOKEN.X_ACCEL_REDIRECT` hands the file to nginx after the check; `FILE_TOKEN.KEY` has no default (was the literal `'None'`). `FullPath.validate_token(token, path)` and `generate_*_token(path)` take the path. See [Files and PDF](../features/files-pdf.md#protected-urls) | **Breaking**: file URLs issued before the upgrade stop working (reload the record); code returning `file.url` without `FullPath.url()` now gets `401` once the web server routes `/media/` to Django | Set `URL_FILE_KEY`; route `/media/` to Django and add the `internal` location (see the doc); sign every file URL with `FullPath.url()` |
| **Documents are scoped per Entity**: `Document` gets `entity`/`branch` (from the signed context), `(entity, tipo, numero)` replaces the global `(tipo, numero)` uniqueness, the target object must belong to the current Entity, `persons/match/` shows only the current Entity's documents. Shipped migration `django_resaas.0004_document_entity_scope`. See [Files and PDF](../features/files-pdf.md#documents-document) | **Breaking**: before, every tenant with `list_document` saw every document; documents that cannot be attributed become invisible | `python manage.py migrate`; attribute any document left without an Entity |
| **Registration hardening** (`register/otp/request/`, `register/`, new `register/username/`): rate limits, OTP attempt limit, password policy, username rules (lowercase, `^[a-z][a-z0-9._]{2,29}$`, refused when taken instead of renamed), lowercase e-mail, a neutral code request (same answer for registered addresses), errors in the `{"error": …}` contract (`alert_error`/`alert_success`/`data` removed), unambiguous login lookup; `users/` needs `add_user` / `change_user` (another user) / `delete_user`. See [Registration](../security/registration.md) | **Breaking** for clients reading `alert_error`, `alert_success` or `data` of these endpoints, expecting a 400 for a registered address, or creating users without `add_user` | Update such clients (quasar_resaas `RegisterPage.vue` is); configure a shared cache for the rate limits; grant `add_user` to the profiles that create users |
| **Model lifecycle events**: `BaseAPIView`'s `perform_create`/`perform_update`/`perform_destroy`/`restore`/`hard_delete` run in `transaction.atomic()` and emit `"<app>.<model>.<action>"` for models with `RESAAS.lifecycle_events`; the notifications catalog returns `lifecycle_events`. See [Model lifecycle events](../features/lifecycle-events.md) | Backward compatible (opt-in; without it only the atomic block is new) | Nothing; opt a model in to use it |
| Core profiles: `Organization Administrator` is gone - its permissions are the `Admin` profile's (a module adding to it, e.g. `hr/profiles.py`, adds to `Admin`); `Branch Administrator` is renamed `Branch Admin` in place (`CORE_RENAMES`, same Group id, members and permissions) | **Breaking** for code that looks a profile up by those names | `python manage.py migrate`; once per environment move any member of `Organization Administrator` to `Admin` and delete that Group |
| **Admin manages its Entity only**: the lib/platform permissions (`PLATFORM_PERMISSIONS` in `saas/profiles.py`: Apps, EntityTypes and their templates, scaffold and Scaffold IDE) are Root's and revoked from `Admin`; `django_resaas/scaffold/` now also needs a permission per action. Without `change_entitytype`, Admin only changes the editable profiles of its own Entity | **Breaking** for Admin users who used EntityType, module or scaffold screens | `python manage.py migrate` (runs the revoke); give a permission back to a custom profile only on purpose |
| The **Scaffold IDE** (`django_resaas/ide/`) needs, besides a staff user, `view_scaffold` to read the workspace and `change_scaffold` to write, apply or run commands (`ActionPermissionMixin`). See [Permissions](../security/permissions.md#legacy-viewsets-per-action-permissions-actionpermissionmixin) | **Breaking** for staff users whose current profile lacks those permissions: `403 permission_denied` | Nothing for Root (it holds them); grant them to another profile only on purpose |
| The **App catalogue** (`django_resaas/apps/`, `django_resaas/resaasapps/`, the `list_app` page) needs a permission per action and only **Root** holds `*_app`: `saas/profiles.py` revokes them from `Admin`. The `System Administrator` profile (a duplicate of `Admin`) no longer exists. `resaasapps/{app}/{model}/schema/` stays open to authenticated users. See [Permissions](../security/permissions.md#legacy-viewsets-per-action-permissions-actionpermissionmixin) | **Breaking** for non-Root groups: they lose the module page and get `403 permission_denied` on those endpoints | `python manage.py migrate` (runs the revoke); delete an existing `System Administrator` Group once (move any member to `Admin` first); give `*_app` back to a custom group only on purpose |
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
