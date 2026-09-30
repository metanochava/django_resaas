from django.contrib import admin

from django_resaas.saas.core.base.admin import BaseAdmin, all_fields
from dev.demo.models import Category


@admin.register(Category)
class CategoryAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)
