"""
Baseline sanity checks for the pytest/pytest-django setup itself.

These exist to prove the test infrastructure (Django app registry, the test
database, the custom AUTH_USER_MODEL) actually works end-to-end, before any
framework-behavior tests are added on top of it.
"""
import pytest
from django.apps import apps
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def test_installed_apps_loaded():
    assert apps.is_installed("django_resaas")
    assert apps.is_installed("hr")


def test_can_create_a_user():
    User = get_user_model()
    user = User.objects.create_user(
        username="sanity-user",
        email="sanity-user@example.com",
        password="sanity-pass-123",
    )
    assert user.pk is not None
    assert User.objects.filter(pk=user.pk).exists()
