# django_resaas/core/base/registry.py
# {module_name: {registered_name: ViewClass}} - see registerView() in
# core/base/views.py, which is what actually populates this.
VIEW_REGISTRY: dict[str, dict[str, type]] = {}
