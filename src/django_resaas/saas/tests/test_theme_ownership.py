"""Themes: templates (no owner) and customized copies owned by one EntityType,
Entity or User (data/theme/views/theme.py). Visibility follows the owner;
`customize` copies a visible theme for one level and applies it there."""
from unittest import mock

import pytest
from rest_framework.test import APIClient

from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.theme import Theme
from django_resaas.saas.models.theme_surface import ThemeSurface
from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db

PERMISSION = "django_resaas.saas.data.theme.views.theme.isPermited"
THEMES = "/api/django_resaas/themes/"


@pytest.fixture
def template():
    theme = Theme.objects.create(name="Ocean", primary="#1E3A8A", secondary="#312E81")
    ThemeSurface.objects.create(theme=theme, area="login")
    return theme


def _plain_client(username):
    user = User.objects.create_user(username=username, email=f"{username}@theme.test", password="Pass-12345")
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


def _customize(client, theme, **body):
    return client.post(f"{THEMES}{theme.id}/customize/", body, format="json")


# ------------------------------------------------------------ customize

def test_a_user_customizes_a_template_for_themselves(template):
    user, client = _plain_client("theme-ana")

    response = _customize(client, template, scope="user", name="Mine", values={"primary": "#0E7C86"})

    assert response.status_code == 201, response.content
    copy = Theme.objects.get(pk=response.json()["id"])
    assert (copy.name, copy.primary, copy.secondary) == ("Mine", "#0E7C86", "#312E81")
    assert copy.owner_user == user and response.json()["owner_scope"] == "user"
    assert ThemeSurface.objects.filter(theme=copy, area="login").exists()
    user.refresh_from_db()
    assert user.theme_id == copy.id
    template.refresh_from_db()
    assert template.primary == "#1E3A8A"  # the template never changes


def test_the_entity_level_needs_change_entity_in_that_entity(bootstrap_tenant, template):
    tenant = bootstrap_tenant("theme-entity")

    with mock.patch(PERMISSION, return_value=False):
        assert _customize(tenant["client"], template, scope="entity").status_code == 403

    response = _customize(tenant["client"], template, scope="entity")

    assert response.status_code == 201, response.content
    tenant["entity"].refresh_from_db()
    assert str(tenant["entity"].theme_id) == response.json()["id"]
    assert Theme.objects.get(pk=response.json()["id"]).owner_entity_id == tenant["entity"].id


def test_another_entity_is_refused(bootstrap_tenant, template):
    tenant = bootstrap_tenant("theme-other-entity")
    other = Entity.objects.create(name="Not mine", entity_type=tenant["entity"].entity_type)

    response = _customize(tenant["client"], template, scope="entity", target=str(other.id))

    assert response.status_code == 403


def test_the_entity_type_level_needs_change_entitytype(bootstrap_tenant, template):
    tenant = bootstrap_tenant("theme-type")
    entity_type = tenant["entity"].entity_type

    with mock.patch(PERMISSION, return_value=False):
        assert _customize(tenant["client"], template, scope="entity_type", target=str(entity_type.id)).status_code == 403

    response = _customize(tenant["client"], template, scope="entity_type", target=str(entity_type.id))

    assert response.status_code == 201, response.content
    entity_type.refresh_from_db()
    assert str(entity_type.theme_id) == response.json()["id"]


@pytest.mark.parametrize("values", [{"primary": 'red;"><script>'}, {"name": "#000000"}, {"id": "#000000"}])
def test_only_customizable_colours_are_accepted(template, values):
    _, client = _plain_client("theme-bad")

    response = _customize(client, template, scope="user", values=values)

    assert response.status_code == 400


# ------------------------------------------------------------ visibility and writes

def test_another_users_theme_is_invisible(template):
    _, owner_client = _plain_client("theme-owner")
    mine = _customize(owner_client, template, scope="user").json()["id"]
    _, other_client = _plain_client("theme-stranger")

    rows = other_client.get(THEMES).json()
    rows = rows.get("results", rows) if isinstance(rows, dict) else rows
    listed = {row["id"] for row in rows}

    assert str(template.id) in listed and mine not in listed
    assert other_client.get(f"{THEMES}{mine}/").status_code == 404
    assert other_client.patch(f"{THEMES}{mine}/", {"primary": "#000000"}, format="json").status_code == 404


def test_the_owner_edits_their_copy_but_not_a_template(template):
    _, client = _plain_client("theme-editor")
    mine = _customize(client, template, scope="user").json()["id"]

    assert client.patch(f"{THEMES}{mine}/", {"primary": "#111111"}, format="json").status_code == 200
    assert client.patch(f"{THEMES}{template.id}/", {"primary": "#111111"}, format="json").status_code == 403
    assert client.delete(f"{THEMES}{template.id}/").status_code == 403
    template.refresh_from_db()
    assert template.primary == "#1E3A8A"


def test_ownership_cannot_be_set_by_the_client(template):
    user, client = _plain_client("theme-sneaky")
    mine = _customize(client, template, scope="user").json()["id"]
    other_type = EntityType.objects.create(name="Elsewhere Type", state="Active")

    client.patch(f"{THEMES}{mine}/", {"owner_entity_type": str(other_type.id), "owner_user": None}, format="json")

    copy = Theme.objects.get(pk=mine)
    assert copy.owner_user_id == user.id and copy.owner_entity_type_id is None


def test_creating_a_theme_needs_add_theme():
    _, client = _plain_client("theme-creator")

    assert client.post(THEMES, {"name": "Free for all"}, format="json").status_code == 403
