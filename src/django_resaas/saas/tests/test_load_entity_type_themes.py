"""manage.py load_entity_type_themes - the type's Theme colours from a JSON
file; idempotent, --dry-run changes nothing. Site content and its
translations are code, not data: a file carrying them is refused."""
import json
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.theme import Theme

pytestmark = pytest.mark.django_db


def _file(tmp_path, data):
    path = tmp_path / "themes.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _run(path, *args):
    out = StringIO()
    call_command("load_entity_type_themes", path, *args, stdout=out)
    return out.getvalue()


@pytest.fixture
def setup(tmp_path):
    entity_type = EntityType.objects.create(name="Site Type", state="Active")
    data = {"themes": {"site type": {"primary": "#1E3A8A", "accent": "#C99A2E"}, "Missing Type": {}}}
    return entity_type, None, _file(tmp_path, data)


def test_loads_the_theme_colours(setup):
    entity_type, _, path = setup

    output = _run(path)

    entity_type.refresh_from_db()
    assert (entity_type.theme.primary, entity_type.theme.accent) == ("#1E3A8A", "#C99A2E")
    assert entity_type.theme.secondary == Theme._meta.get_field("secondary").default
    assert "Missing Type" in output


def test_rerun_is_idempotent(setup):
    entity_type, _, path = setup
    _run(path)
    theme_id = EntityType.objects.get(pk=entity_type.pk).theme_id

    output = _run(path)

    assert "themes: 1" in output
    assert EntityType.objects.get(pk=entity_type.pk).theme_id == theme_id


def test_dry_run_changes_nothing(setup):
    entity_type, _, path = setup
    theme_before = entity_type.theme and (entity_type.theme_id, entity_type.theme.primary)

    output = _run(path, "--dry-run")

    entity_type.refresh_from_db()
    assert output.startswith("[dry-run]")
    assert (entity_type.theme and (entity_type.theme_id, entity_type.theme.primary)) == theme_before


def test_own_theme_is_updated_in_place(setup):
    entity_type, _, path = setup
    theme = Theme.objects.create(name="Own", secondary="#123456")
    entity_type.theme = theme
    entity_type.save()

    _run(path)

    entity_type.refresh_from_db()
    theme.refresh_from_db()
    assert entity_type.theme_id == theme.pk
    assert (theme.primary, theme.secondary) == ("#1E3A8A", "#123456")


def test_shared_theme_is_copied_not_changed(setup):
    entity_type, _, path = setup
    shared = Theme.objects.create(name="Shared", secondary="#123456")
    entity_type.theme = shared
    entity_type.save()
    EntityType.objects.create(name="Other Type", state="Active", theme=shared)

    _run(path)

    entity_type.refresh_from_db()
    shared.refresh_from_db()
    assert shared.primary == Theme._meta.get_field("primary").default
    assert entity_type.theme_id != shared.pk
    assert (entity_type.theme.primary, entity_type.theme.secondary) == ("#1E3A8A", "#123456")


@pytest.mark.parametrize("data, message", [
    ({"themes": {"Site Type": {"id": "x"}}}, "Unknown theme fields"),
    ({"themes": {"Site Type": {"not_a_colour": "#000"}}}, "Unknown theme fields"),
    ({"themes": ["Site Type"]}, "must be an object"),
    # the site content and its translations are code, not data
    ({"sites": {"Site Type": {}}}, "registerEntityTypeSiteContent"),
    ({"translations": {"pt-pt": {}}}, "static lang files"),
])
def test_invalid_files_are_rejected(setup, tmp_path, data, message):
    with pytest.raises(CommandError, match=message):
        _run(_file(tmp_path, data))
