
class TenantContextMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tipo_entidade_id = request.headers.get('ET')
        request.entidade_id = request.headers.get('E')
        request.sucursal_id = request.headers.get('S')
        request.group_id = request.headers.get('G')
        request.lang_id = request.headers.get('L')

        return self.get_response(request)
