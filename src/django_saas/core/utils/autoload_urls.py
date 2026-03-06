from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.viewsets import ViewSetMixin
from django_saas.core.base.registry import VIEW_REGISTRY


def build_saas_urls():
    router = DefaultRouter()
    extra_patterns = []

    for module, views in VIEW_REGISTRY.items():

        for name, view_cls in views.items():
            prefix = f"{module}/{name}"

            if issubclass(view_cls, ViewSetMixin):
                router.register(prefix, view_cls, basename=prefix.replace("/", "_"))
            else:
                extra_patterns.append(
                    path(f"{prefix}/", view_cls.as_view())
                )

    return router, extra_patterns
