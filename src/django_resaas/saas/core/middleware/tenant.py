from django_resaas.saas.core.tenant.context import ResaasContextService
from django_resaas.saas.core.tenant.current import reset_current_entity_id, set_current_entity_id


class TenantContextMiddleware:
    HEADER = "X-RESAAS-Context"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant_context = None
        request.tenant_context_error = None
        request.entity_type_id = None
        request.entity_id = None
        request.branch_id = None
        request.group_id = None
        request.lang_id = request.headers.get("L")

        token = request.headers.get(self.HEADER)

        if token:
            try:
                payload = ResaasContextService.decode(token)
                request.tenant_context = payload
                request.entity_type_id = payload.get("entity_type_id")
                request.entity_id = payload.get("entity_id")
                request.branch_id = payload.get("branch_id")
                request.group_id = payload.get("group_id")
            except Exception as exc:
                request.tenant_context_error = exc

        marker = set_current_entity_id(request.entity_id)

        try:
            return self.get_response(request)
        finally:
            reset_current_entity_id(marker)