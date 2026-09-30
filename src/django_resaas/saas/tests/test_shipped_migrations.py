"""The framework ships its migrations (docs/deployment/upgrading.md): the
models and the shipped migrations must always agree, and an environment
created before can be aligned with resaas_migrations_rebaseline."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import override_settings

from django_resaas.saas.management.commands.resaas_migrations_rebaseline import framework_labels, leaf_of

pytestmark = pytest.mark.django_db


@override_settings(MIGRATION_MODULES={})  # the real migrations, not pytest's --nomigrations stand-in
def test_every_model_change_has_a_shipped_migration():
    """A model changed without its migration fails here (and in CI)."""
    out = StringIO()

    call_command("makemigrations", "django_resaas", "notifications", check=True, dry_run=True, stdout=out)

    assert "No changes detected" in out.getvalue()


def test_framework_apps_are_detected_by_package():
    assert framework_labels() == {"django_resaas", "notifications"}
    # an application's modules (demo here, hr in an application) are not framework apps
    assert "demo" not in framework_labels()


def test_leaf_is_the_migration_nothing_else_depends_on():
    class Migration:
        app_label = "x"

        def __init__(self, deps):
            self.dependencies = deps

    migrations = {
        ("x", "0001_initial"): Migration([]),
        ("x", "0002_more"): Migration([("x", "0001_initial")]),
    }

    assert leaf_of({"0001_initial", "0002_more"}, migrations) == "0002_more"


@override_settings(MIGRATION_MODULES={})
def test_rebaseline_dry_run_changes_nothing_on_an_aligned_project():
    out = StringIO()

    call_command("resaas_migrations_rebaseline", stdout=out)

    text = out.getvalue()
    assert "Project migration dependencies to repoint: 0" in text
    assert "Dry run - nothing changed" in text
