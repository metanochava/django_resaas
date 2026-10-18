"""create_model_permissions (core/signals/permissions.py): one read and one
bulk insert instead of a get_or_create per permission - same rows, same
names, idempotent, Root holds them all."""
import pytest
from django.apps import apps
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test.utils import CaptureQueriesContext

from django_resaas.saas.core.signals.permissions import create_model_permissions
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.group import Group
from django_resaas.saas.models.language import Language

pytestmark = pytest.mark.django_db


def _sync():
    create_model_permissions(sender=None, app_config=apps.get_app_config("django_resaas"))


@pytest.fixture
def entity_type():
    # the sync no-ops until an EntityType exists
    return EntityType.objects.create(name="Sync Type", state="Active")


def test_creates_the_model_and_scaffold_permissions_and_gives_them_to_root(entity_type):
    _sync()
    ct = ContentType.objects.get_for_model(Language)
    root = Group.objects.get(name="Root")

    for codename in ("view", "add", "change", "delete", "list", "pdf", "pdf_list", "restore", "hard_delete"):
        perm = Permission.objects.get(content_type=ct, codename=f"{codename}_language")
        assert root.permissions.filter(pk=perm.pk).exists()

    assert root.permissions.filter(codename="view_scaffold", content_type__model="command").exists()


def test_running_again_creates_nothing_and_keeps_existing_names(entity_type):
    _sync()
    ct = ContentType.objects.get_for_model(Language)
    Permission.objects.filter(content_type=ct, codename="pdf_language").update(name="Renamed by hand")
    count = Permission.objects.count()

    _sync()

    assert Permission.objects.count() == count
    assert Permission.objects.get(content_type=ct, codename="pdf_language").name == "Renamed by hand"


def test_a_deleted_permission_is_recreated(entity_type):
    _sync()
    ct = ContentType.objects.get_for_model(Language)
    Permission.objects.filter(content_type=ct, codename="restore_language").delete()

    _sync()

    perm = Permission.objects.get(content_type=ct, codename="restore_language")
    assert Group.objects.get(name="Root").permissions.filter(pk=perm.pk).exists()


def test_query_count_does_not_grow_with_the_number_of_models(entity_type):
    _sync()

    with CaptureQueriesContext(connection) as queries:
        _sync()

    # a get_or_create per permission was 9+ queries per model
    models = sum(1 for _ in apps.get_models())
    assert len(queries) < models
