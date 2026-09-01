"""
Data-safety test for migration 0002_modelextraaction_ownership_and_identity:
app/model/action become NOT NULL there, preceded by a RunPython step that
must clean up any pre-existing row missing one of them (such a row can't
be addressed by (app, model, action) anyway - see the migration's own
docstring). This locks in that the cleanup step actually runs and that
rows WITH all three survive untouched.

Uses Django's MigrationExecutor directly (no extra test dependency) to
migrate back to the state right before 0002, insert data with the
*historical* model, migrate forward, and assert on the result - the
standard way to test a data migration in isolation.
"""
import pytest
from django.db.migrations.executor import MigrationExecutor
from django.db import connection

pytestmark = pytest.mark.django_db(transaction=True)


def test_rows_missing_app_model_or_action_are_deleted_by_the_migration():
    executor = MigrationExecutor(connection)

    # go back to right before 0002
    executor.migrate([("django_resaas", "0001_initial")])
    executor.loader.build_graph()

    OldModelExtraAction = executor.loader.project_state(
        ("django_resaas", "0001_initial")
    ).apps.get_model("django_resaas", "ModelExtraAction")

    valid = OldModelExtraAction.objects.create(
        app="demo", model="product", action="archive"
    )
    missing_app = OldModelExtraAction.objects.create(
        app=None, model="product", action="broken1"
    )
    missing_model = OldModelExtraAction.objects.create(
        app="demo", model=None, action="broken2"
    )
    missing_action = OldModelExtraAction.objects.create(
        app="demo", model="product", action=None
    )

    # forward to (and past) 0002
    executor = MigrationExecutor(connection)
    executor.migrate([("django_resaas", "0002_modelextraaction_ownership_and_identity")])
    executor.loader.build_graph()

    NewModelExtraAction = executor.loader.project_state(
        ("django_resaas", "0002_modelextraaction_ownership_and_identity")
    ).apps.get_model("django_resaas", "ModelExtraAction")

    remaining_ids = set(
        NewModelExtraAction.objects.values_list("id", flat=True)
    )

    assert valid.id in remaining_ids
    assert missing_app.id not in remaining_ids
    assert missing_model.id not in remaining_ids
    assert missing_action.id not in remaining_ids

    # bring the DB schema back to the real, full leaf state (every app,
    # not just django_resaas) for any test that runs after this one
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
