from django.apps import AppConfig
class DjangoResaasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "django_resaas"
    verbose_name = "Django SaaS"

    def ready(self):
        self.load_permissions()
        # self.load_admin()

    def load_permissions(self):
        import django_resaas.core.signals.permissions

    def load_admin(self):
        from django_resaas.core.base.mixins.admin.auto import register_all_models
        register_all_models()