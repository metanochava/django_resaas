class DiskManegarService:
    def __init__(self, request):
        self.request = request
        self.entity_id = request.entity_id
        self.branch_id = request.branch_id
        self.user = request.user