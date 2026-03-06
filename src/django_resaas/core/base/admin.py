from django.contrib import admin

@admin.action(description="Restaurar selecionados")
def restore_selected(modeladmin, request, queryset):
    queryset.restore()

@admin.action(description="Soft delete selecionados")
def soft_delete_selected(modeladmin, request, queryset):
    queryset.soft_delete()

class BaseAdmin(admin.ModelAdmin):
    actions = [restore_selected, soft_delete_selected]

    def get_queryset(self, request):
        return self.model.all_objects.all()