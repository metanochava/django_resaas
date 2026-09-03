"""
Pytest bootstrap for the test suite.

Sets safe defaults for the environment variables `dev.settings` reads via
`os.environ.get(...)` with no fallback (SECRET_KEY, TIME_ZONE, ...), so the
suite runs standalone without requiring a local `.env` file. Real deployments
still supply their own values via `.env` / the environment as usual.
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("TIME_ZONE", "UTC")
os.environ.setdefault("SQL_ENGINE", "sqlite3")
os.environ.setdefault("SQL_DATABASE", ":memory:")
os.environ.setdefault("DOCKER", "YES")  # skip .env loading, we set what we need above

import pytest


@pytest.fixture
def activate_module():
    """Activates a per-client module (App + EntityApp) for an entity - the
    same thing a real deployment does to turn on an optional module beyond
    what BootstrapService activates by default ("hr" only). See the
    state="Active" note in src/django_resaas/core/services/tests/
    test_bootstrap_service.py for why this must be the string "Active"."""

    def _activate(entity, name):
        from django_resaas.engine.models.app import App
        from django_resaas.engine.models.entity_app import EntityApp

        app, _ = App.objects.get_or_create(name=name, defaults={"state": "Active"})
        EntityApp.objects.get_or_create(
            entity=entity, app=app, defaults={"state": "Active"}
        )
        return app

    return _activate


@pytest.fixture
def bootstrap_tenant(activate_module):
    """Factory fixture: bootstraps a fresh tenant (Entity/Branch/Root+Guest
    groups + a user in Root) the same way `manage.py create_entity` does
    (BootstrapService), re-runs the permission-creation signal (it no-ops
    until an EntityType exists - see docs/development/management-commands.md
    and src/dev/README.md), and returns a signed tenant context + a ready
    APIClient. Call it once per test with a unique `username`; pass
    `modules=("hr",)` etc. for anything beyond what BootstrapService already
    activates by default."""

    def _bootstrap(username, modules=()):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient

        from django_resaas.engine.core.services.bootstrap_service import BootstrapService
        from django_resaas.engine.core.signals.permissions import create_model_permissions
        from django_resaas.engine.core.tenant.context import ResaasContextService
        from django_resaas.engine.models.branch_user_group import BranchUserGroup
        from django_resaas.engine.models.group import Group

        User = get_user_model()

        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="pass-12345",
        )

        bootstrap = BootstrapService.run(
            entity_type="Test Type",
            entity=f"{username}-tenant",
            branch="Main",
            user=user,
            group="Admin",
        )
        entity, branch = bootstrap["entity"], bootstrap["branch"]

        class _FakeAppConfig:
            name = "django_resaas.engine"
            label = "django_resaas"

        create_model_permissions(sender=None, app_config=_FakeAppConfig())

        root_group = Group.objects.get(name="Root")
        BranchUserGroup.objects.get_or_create(
            user=user, branch=branch, group=root_group, defaults={"state": 1}
        )

        for module_name in modules:
            activate_module(entity, module_name)

        context = ResaasContextService.issue(
            user=user, entity_id=entity.id, branch_id=branch.id, group_id=root_group.id
        )

        client = APIClient()
        client.force_authenticate(user=user)
        client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")

        return {
            "user": user,
            "entity": entity,
            "branch": branch,
            "root_group": root_group,
            "context": context,
            "client": client,
        }

    return _bootstrap
