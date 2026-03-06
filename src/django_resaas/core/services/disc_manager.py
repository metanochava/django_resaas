class DiskManegarService:
    def __init__(self, request):
        self.request = request
        self.entidade_id = request.entidade_id
        self.sucursal_id = request.sucursal_id
        self.user = request.user