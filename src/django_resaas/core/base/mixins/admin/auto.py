

from django.contrib import admin
from django.apps import apps
from django_resaas.core.base.admin import BaseAdmin


def register_all_models():
    for model in apps.get_models():

        if model._meta.abstract or model._meta.proxy:
            continue

        # 🔥 SOLUÇÃO AQUI
        if model in admin.site._registry:
            continue

        admin.site.register(model, BaseAdmin)