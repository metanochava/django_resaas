"""Test helpers for projects and modules built on RESAAS (public API).

A tenant bootstrapped the way `manage.py create_entity` does it
(BootstrapService): Entity, Branch, a user in the Root group, a signed tenant
context and a ready APIClient.

    from django_resaas.testing import bootstrap_tenant

    tenant = bootstrap_tenant("alice", modules=("sales",))
    tenant["client"].get("/api/sales/invoices/")

With pytest, enable the fixtures in your conftest.py:

    pytest_plugins = ["django_resaas.testing.pytest_plugin"]

and use `bootstrap_tenant` / `activate_module` as fixtures.
"""

__all__ = ["activate_module", "bootstrap_tenant"]


def activate_module(entity, name):
    """Activates a module (App + EntityApp) for an Entity - what a deployment
    does to turn on a module beyond the defaults. `state` must be "Active"."""
    from django_resaas.saas.models.app import App
    from django_resaas.saas.models.entity_app import EntityApp

    app, _ = App.objects.get_or_create(name=name, defaults={"state": "Active"})
    EntityApp.objects.get_or_create(entity=entity, app=app, defaults={"state": "Active"})
    return app


def bootstrap_tenant(username, modules=()):
    """A fresh tenant for a test. Use a unique `username` per call; `modules`
    are activated for the Entity (e.g. ("sales",)). Returns a dict with user,
    entity, branch, root_group, context and client."""
    from django.apps import apps
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    from django_resaas.saas.core.services.bootstrap_service import BootstrapService
    from django_resaas.saas.core.signals.permissions import create_model_permissions
    from django_resaas.saas.core.tenant.context import ResaasContextService
    from django_resaas.saas.models.branch_user_group import BranchUserGroup
    from django_resaas.saas.models.group import Group

    user = get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="pass-12345",
    )

    bootstrap = BootstrapService.run(
        entity_type="Test Type", entity=f"{username}-tenant", branch="Main", user=user, group="Admin",
    )
    entity, branch = bootstrap["entity"], bootstrap["branch"]

    # the permission sync no-ops until an EntityType exists: run it now that one does
    create_model_permissions(sender=None, app_config=apps.get_app_config("django_resaas"))

    root_group = Group.objects.get(name="Root")
    BranchUserGroup.objects.get_or_create(user=user, branch=branch, group=root_group, defaults={"state": "Active"})

    for module_name in modules:
        activate_module(entity, module_name)

    context = ResaasContextService.issue(user=user, entity_id=entity.id, branch_id=branch.id, group_id=root_group.id)

    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")

    return {"user": user, "entity": entity, "branch": branch, "root_group": root_group,
            "context": context, "client": client}
