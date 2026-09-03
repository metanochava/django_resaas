

from django.conf import settings
from django.contrib import admin
from django.apps import apps
from django_resaas.engine.core.base.admin import BaseAdmin


def register_all_models():
    my_apps = getattr(settings, "MY_APPS", [])
    allowed_apps = [app.split(".")[-1] for app in my_apps]

    for model in apps.get_models():

        if model._meta.abstract or model._meta.proxy:
            continue

        if model._meta.app_label not in allowed_apps:
            continue

        if model in admin.site._registry:
            continue

        admin.site.register(model, BaseAdmin)