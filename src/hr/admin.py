
from django.contrib import admin
from django_resaas.core.base.admin import BaseAdmin, all_fields
from hr.models.employee import Employee

admin.site.site_title = 'HR'
admin.site.index_title = 'HR'

@admin.register(Employee)
class EmployeeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)