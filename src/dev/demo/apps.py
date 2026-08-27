from django.apps import AppConfig


class DemoConfig(AppConfig):
    """
    Minimal example app proving the full django_resaas flow end to end:
    model -> BaseSerializer -> BaseAPIView -> ResaasSchemaBuilder -> JSON.

    Dev-only: not part of the published django_resaas package.
    """

    default_auto_field = "django.db.models.BigAutoField"

    name = "dev.demo"

    label = "demo"

    verbose_name = "Demo"
