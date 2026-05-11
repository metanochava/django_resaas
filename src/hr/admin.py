
from django_resaas.core.base.admin import BaseAdmin
from django.contrib import admin

admin.site.site_title = 'HR'
admin.site.index_title = 'HR'

def all_fields(model):
    return [field.name for field in model._meta.fields]

