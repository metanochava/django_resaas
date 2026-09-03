"""
Data-integrity test for `ModelExtraAction.app/model/action`: these three
fields together are the row's logical identity (see the model's own
docstring) and must never be null.

This used to be a two-phase MigrationExecutor test exercising migration
0002_modelextraaction_ownership_and_identity's RunPython cleanup step
directly (which deleted any pre-existing row missing one of the three
before adding the NOT NULL constraint). An external release process
squashed that migration into 0001_initial during this session - a fresh
install now creates the table with the constraint from the start, so
there is no longer an intermediate "constraint not yet applied" state to
migrate through and test. The cleanup step itself only ever mattered for
databases that already had bad rows before 0002 originally shipped -
already-migrated databases keep that history in their own
`django_migrations` table regardless of what the current migration files
look like, so nothing about upgrading existing deployments changes here.

What's still worth guarding, and squash-proof: the model-level NOT NULL
constraint itself.
"""
import pytest
from django.db import IntegrityError

from django_resaas.engine.models.model_extra_action import ModelExtraAction

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("missing_field", ["app", "model", "action"])
def test_app_model_action_are_required(missing_field):
    fields = {"app": "demo", "model": "product", "action": "archive"}
    fields[missing_field] = None

    with pytest.raises(IntegrityError):
        ModelExtraAction.objects.create(**fields)


def test_row_with_all_three_fields_saves_fine():
    row = ModelExtraAction.objects.create(app="demo", model="product", action="archive")
    assert row.id is not None
