from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_resaas.engine.core.tenant.context import ResaasContextService


class ResaasContextAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = ResaasContextService.issue(
            user=request.user,
            # entity_id=request.data.get("entity_type_id"),
            entity_id=request.data.get("entity_id"),
            branch_id=request.data.get("branch_id"),
            group_id=request.data.get("group_id"),
        )
        return Response(result)