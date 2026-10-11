"""IDEWorkspaceAPIView (django_resaas/ide/, the Scaffold IDE): besides being
staff (IsAdminUser) and enabled (SCAFFOLD_IDE_ENABLED / DEBUG), every action
needs its RESAAS permission in the signed context - view_scaffold to read the
workspace, change_scaffold to write, apply or run a command."""
import pytest
from django.contrib.auth import get_user_model

from django_resaas.saas.tests.test_permission_api_security import _actor

pytestmark = pytest.mark.django_db

URL = "/api/django_resaas/ide/"

READS = [
    ("get", "", None),
    ("get", "roots/", None),
    ("get", "tree/?root=django_resaas", None),
    ("get", "read/?root=django_resaas&path=x.py", None),
    ("get", "commands/", None),
    ("post", "validate/", {"files": []}),
]
WRITES = [
    ("post", "write/", {"root": "django_resaas", "path": "x.py", "content": ""}),
    ("post", "apply/", {"files": []}),
    ("post", "run/", {"key": "check"}),
]


def _staff_actor(tenant, username, *codenames):
    """A staff user (passes IsAdminUser) whose group holds exactly `codenames`:
    any 403 left is the RESAAS permission check."""
    client = _actor(tenant, username, *codenames)
    user = get_user_model().objects.get(username=username)
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    client.force_authenticate(user=user)
    return client


def _denied(response):
    assert response.status_code == 403, response.status_code
    assert response.json()["error"]["code"] == "permission_denied"


@pytest.fixture(autouse=True)
def _ide_on(settings):
    settings.DEBUG = True


@pytest.mark.parametrize("method,path,body", READS + WRITES)
def test_staff_without_the_permission_is_refused(bootstrap_tenant, method, path, body):
    slug = path.split("/")[0] or "list"
    tenant = bootstrap_tenant(f"ide-perm-{method}-{slug}")
    client = _staff_actor(tenant, f"ide-perm-{method}-{slug}-actor")

    _denied(getattr(client, method)(URL + path, body, format="json"))


@pytest.mark.parametrize("method,path,body", WRITES)
def test_view_scaffold_reads_but_cannot_write(bootstrap_tenant, method, path, body):
    slug = path.split("/")[0]
    tenant = bootstrap_tenant(f"ide-view-{slug}")
    client = _staff_actor(tenant, f"ide-view-{slug}-actor", "view_scaffold")

    assert client.get(URL + "roots/").status_code == 200
    _denied(getattr(client, method)(URL + path, body, format="json"))


def test_a_non_staff_user_is_still_refused_even_with_the_permissions(bootstrap_tenant):
    tenant = bootstrap_tenant("ide-not-staff")
    client = _actor(tenant, "ide-not-staff-actor", "view_scaffold", "change_scaffold")

    assert client.get(URL + "roots/").status_code == 403


def test_root_uses_the_ide(bootstrap_tenant):
    tenant = bootstrap_tenant("ide-root")
    tenant["user"].is_staff = True
    tenant["user"].save()

    assert tenant["client"].get(URL + "roots/").status_code == 200
    assert tenant["client"].get(URL + "commands/").status_code == 200


# ------------------------------------------------------------------ scaffold/

SCAFFOLD = "/api/django_resaas/scaffold/"


@pytest.mark.parametrize("method,path,body", [
    ("get", "", None),
    ("post", "preview/", {}),
    ("post", "", {}),
    ("put", "x/", {}),
    ("post", "migrate/", {"app": "x"}),
    ("post", "permissions/", {"app": "x", "model": "Y", "actions": []}),
    ("delete", "x/", None),
])
def test_scaffold_actions_need_their_permission(bootstrap_tenant, method, path, body):
    slug = (path.split("/")[0] or "list").replace(".", "-").lower()
    tenant = bootstrap_tenant(f"scaf-perm-{method}-{slug}")
    client = _staff_actor(tenant, f"scaf-perm-{method}-{slug}-actor")

    _denied(getattr(client, method)(SCAFFOLD + path, body, format="json"))


def test_view_scaffold_cannot_generate_or_delete(bootstrap_tenant):
    tenant = bootstrap_tenant("scaf-view-only")
    client = _staff_actor(tenant, "scaf-view-only-actor", "view_scaffold")

    assert client.get(SCAFFOLD).status_code == 200
    _denied(client.post(SCAFFOLD, {}, format="json"))
    _denied(client.post(SCAFFOLD + "migrate/", {"app": "x"}, format="json"))
    _denied(client.delete(SCAFFOLD + "x/"))

