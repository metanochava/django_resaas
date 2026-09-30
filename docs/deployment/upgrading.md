# Upgrading

## Framework migrations are shipped with the package

`django_resaas` ships its own migrations, one `0001_initial` per framework app
(`django_resaas`, `hr`, `notifications`), in `src/django_resaas/*/migrations/`.
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
`("django_resaas", "0001_initial")` / `("hr", "0001_initial")`, which still exist
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
| `makemigrations --check` reports changes in `django_resaas`/`hr`/`notifications` after the upgrade | The database was not fully migrated with the previous version (step 0), or the project runs an older package: stop, restore the backup, redo from step 0 |
| `makemigrations` creates files inside the installed package | Never commit or keep those. The framework's migrations come from the package. Report the model change upstream |

## Framework developers: model changes need a migration

Changing a model of the framework now means shipping its migration:

```bash
cd src
python3 manage.py makemigrations django_resaas hr notifications
```

`saas/tests/test_shipped_migrations.py` fails when a model changed without its
migration.
