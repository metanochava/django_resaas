
class TenantContextMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.entity_type_id = request.headers.get('ET')
        request.entity_id = request.headers.get('E')
        request.branch_id = request.headers.get('S')
        request.group_id = request.headers.get('G')
        request.lang_id = request.headers.get('L')

        return self.get_response(request)
