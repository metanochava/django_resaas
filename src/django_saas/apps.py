from django.apps import AppConfig
class DjangoSaasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "django_saas"
    verbose_name = "Django SaaS"

    def ready(self):
        import django_saas.core.signals