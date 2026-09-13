class DiskManegarService:
    def __init__(self, request):
        self.request = request
        self.entity_id = request.entity_id
        self.branch_id = request.branch_id
        self.user = request.user

    @staticmethod
    def get_entity_usage(entity_id):
        """Real storage usage for `entity_id`, in bytes, broken down by
        File.funcionalidade (Logo/Photo/Cover/File/Profile) - the only
        ownership signal File records today. Read-only aggregation for
        display purposes (Entity edit page's storage chart) - does not
        touch upload-time quota enforcement, which this service never
        actually implemented (freeSpace/recoverSpace/updateSpace,
        called elsewhere in this codebase, don't exist as callable
        methods here - a pre-existing, separate gap)."""
        from django.db.models import Sum

        from django_resaas.saas.models.file import File

        queryset = File.objects.filter(entity_id=entity_id)

        total_bytes = queryset.aggregate(total=Sum("size"))["total"] or 0

        breakdown = (
            queryset.values("funcionalidade")
            .annotate(bytes=Sum("size"))
            .order_by("-bytes")
        )

        return {
            "total_bytes": total_bytes,
            "breakdown": [
                {"category": row["funcionalidade"] or "File", "bytes": row["bytes"] or 0}
                for row in breakdown
            ],
        }