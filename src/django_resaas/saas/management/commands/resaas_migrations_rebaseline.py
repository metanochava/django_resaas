"""One-off upgrade to framework migrations shipped with the package.

Until 0.0.621 the framework's migrations were not versioned: every
environment generated its own (0001_initial, 0002_..., with names that differ
from one environment to another). The package now ships its migrations
(one 0001_initial per framework app, with the same schema - see
docs/deployment/upgrading.md). On an environment created before that:

- rows in django_migrations point at framework migrations that no longer
  exist (they are pruned);
- the project's own app migrations (generated locally) may depend on them,
  e.g. ('django_resaas', '0003_entity_founded_on_...'): each such dependency
  is pointed at the latest migration the framework ships, whose schema is the
  same.

Dry run by default (prints the plan, changes nothing). --apply rewrites the
project's migration files (only files under BASE_DIR - never an installed
package) and prunes the stale rows. Run it after installing the new package,
with the database fully migrated by the previous version, and with a backup.
"""
import re
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder

FRAMEWORK_PREFIXES = ("django_resaas", "resaas_")


def framework_labels():
    return {
        config.label for config in apps.get_app_configs()
        if config.name.split(".")[0].startswith(FRAMEWORK_PREFIXES)
    }


def leaf_of(names, migrations):
    """The migration of an app no other migration of that app depends on."""
    app = next(iter(migrations.values())).app_label if migrations else None
    depended = {dep[1] for m in migrations.values() for dep in m.dependencies if dep[0] == app}
    leaves = sorted(set(names) - depended)
    return leaves[-1] if leaves else None


class Command(BaseCommand):
    help = "Align an existing environment with the framework's shipped migrations (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Rewrite project migration files and prune stale rows.")

    def handle(self, *args, **options):
        apply = options["apply"]
        labels = framework_labels()
        base_dir = Path(settings.BASE_DIR).resolve()

        # disk only: the graph may not build yet (that is what this fixes)
        loader = MigrationLoader(None, ignore_no_migrations=True, load=False)
        loader.load_disk()
        disk = loader.disk_migrations

        shipped = {label: {name for (app, name) in disk if app == label} for label in labels}
        leaves = {
            label: leaf_of(names, {k: v for k, v in disk.items() if k[0] == label})
            for label, names in shipped.items() if names
        }

        # 1. project migrations depending on framework migrations that are gone
        rewrites = []
        for (app, name), migration in disk.items():
            if app in labels:
                continue
            path = Path(__import__(migration.__module__, fromlist=["_"]).__file__).resolve()
            if base_dir not in path.parents:
                continue  # an installed package: never touched
            for dep_app, dep_name in migration.dependencies:
                if dep_app in labels and dep_name not in shipped.get(dep_app, set()) and dep_name != "__first__":
                    rewrites.append((path, dep_app, dep_name, leaves.get(dep_app)))

        # 2. stale django_migrations rows of framework apps
        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations() if recorder.has_table() else {}
        stale = sorted((app, name) for (app, name) in applied if app in labels and name not in shipped.get(app, set()))
        missing = sorted(
            (label, leaf) for label, leaf in leaves.items()
            if applied and not any(app == label for (app, _n) in applied)
        )

        self.stdout.write(self.style.MIGRATE_HEADING("Framework apps: " + ", ".join(sorted(labels))))
        for label in sorted(leaves):
            self.stdout.write(f"  {label}: ships {len(shipped[label])} migration(s), latest {leaves[label]}")

        self.stdout.write(self.style.MIGRATE_HEADING(f"Project migration dependencies to repoint: {len(rewrites)}"))
        for path, dep_app, dep_name, leaf in rewrites:
            self.stdout.write(f"  {path.relative_to(base_dir)}: ('{dep_app}', '{dep_name}') -> ('{dep_app}', '{leaf}')")
            if leaf is None:
                self.stderr.write(self.style.ERROR(f"    {dep_app} ships no migrations: cannot repoint"))

        self.stdout.write(self.style.MIGRATE_HEADING(f"Stale django_migrations rows to prune: {len(stale)}"))
        for app, name in stale:
            self.stdout.write(f"  {app}.{name}")
        if missing:
            self.stdout.write(self.style.WARNING(
                "Framework apps with no applied migration (a new app - `migrate` creates it): "
                + ", ".join(label for label, _leaf in missing)))

        if not apply:
            self.stdout.write(self.style.WARNING("Dry run - nothing changed. Re-run with --apply (after a backup)."))
            return

        if any(leaf is None for *_x, leaf in rewrites):
            self.stderr.write(self.style.ERROR("Aborted: some dependencies cannot be repointed."))
            return

        for path, dep_app, dep_name, leaf in rewrites:
            text = path.read_text(encoding="utf-8")
            pattern = re.compile(r"""\(\s*(['"])%s\1\s*,\s*(['"])%s\2\s*\)""" % (re.escape(dep_app), re.escape(dep_name)))
            new_text, count = pattern.subn(f'("{dep_app}", "{leaf}")', text)
            if count:
                path.write_text(new_text, encoding="utf-8")

        if stale:
            with connection.cursor() as cursor:
                for app, name in stale:
                    cursor.execute(
                        f"DELETE FROM {connection.ops.quote_name(recorder.Migration._meta.db_table)} WHERE app = %s AND name = %s",
                        [app, name],
                    )

        self.stdout.write(self.style.SUCCESS(
            f"Done: {len(rewrites)} dependency(ies) repointed, {len(stale)} stale row(s) pruned. "
            "Now run `migrate` and `makemigrations --check`."))
