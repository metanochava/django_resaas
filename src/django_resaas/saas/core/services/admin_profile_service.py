"""The Admin profile holds every permission of the business modules its
Entities use.

When a module is activated for an Entity (EntityApp), the "Admin" profile gets
every permission of that module: its models' CRUD, actions and dashboards.
Admin is one profile shared by every Entity; what an Entity reaches is still
decided by the modules active for it (installed != active per Entity, CLAUDE.md
#17) and the request's tenant scope - a permission is a capability, never a
scope.

Never granted:
- the framework's own modules (bootstrap_service.FRAMEWORK_MODULES: the
  django_resaas core and notifications): the core profiles decide
  Admin's core permissions (saas/profiles.py CORE_PROFILES);
- the platform's permissions (saas/profiles.py PLATFORM_PERMISSIONS: the
  module catalogue, entity types, scaffold) - Root's only.

Called where a module is activated for an Entity (EntityAPIView.create /
addApp, AppAPIView.entities, the module scaffold) and after every migrate
for the modules already active (new models bring new permissions).
"""
import logging

from django.apps import apps as django_apps

logger = logging.getLogger(__name__)

ADMIN_GROUP = "Admin"


def _label_of(app_name):
    """The Django app label of an App catalogue name (AppConfig.name, e.g.
    "hospitality" or "django_resaas.saas"), or None when not installed."""
    for config in django_apps.get_app_configs():
        if config.name == app_name or config.label == app_name:
            return config.label
    return None


def grant_app(app_name):
    """Give the Admin profile every permission of this business module.
    Idempotent; returns how many permissions it did not have yet."""
    from django.contrib.auth.models import Permission

    from django_resaas.saas.models.group import Group
    from django_resaas.saas.profiles import PLATFORM_PERMISSIONS

    from django_resaas.saas.core.services.bootstrap_service import FRAMEWORK_MODULES

    label = _label_of(app_name)
    if not label or label in FRAMEWORK_MODULES:
        return 0
    group = Group.objects.filter(name=ADMIN_GROUP).first()
    if group is None:
        return 0
    permissions = Permission.objects.filter(content_type__app_label=label).exclude(codename__in=PLATFORM_PERMISSIONS)
    missing = list(permissions.exclude(id__in=group.permissions.values("id")))
    if missing:
        group.permissions.add(*missing)
        logger.info("Admin profile: %s permissions of %s granted", len(missing), app_name)
    return len(missing)


def grant_active_apps():
    """grant_app() for every module active for at least one Entity."""
    from django_resaas.saas.models.app import App

    names = App.objects.filter(entityapp__state="Active").values_list("name", flat=True).distinct()
    return {name: grant_app(name) for name in names}


def on_post_migrate(sender, app_config=None, **kwargs):
    """After a module migrates (it may have new models, so new permissions):
    when it is active for an Entity, Admin gets them too."""
    if app_config is None:
        return
    from django_resaas.saas.models.app import App

    try:
        active = App.objects.filter(name=app_config.name, entityapp__state="Active").exists()
    except Exception:  # the tables may not exist yet on the very first migrate
        return
    if active:
        # the module's model permissions first: django.contrib.auth's own
        # post_migrate may run after this one
        from django.contrib.auth.management import create_permissions

        create_permissions(app_config, verbosity=0, using=kwargs.get("using", "default"))
        grant_app(app_config.name)
