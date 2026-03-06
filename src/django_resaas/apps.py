from django.apps import AppConfig
class DjangoSaasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "django_resaas"
    verbose_name = "Django SaaS"

    def ready(self):
        import django_resaas.core.signals