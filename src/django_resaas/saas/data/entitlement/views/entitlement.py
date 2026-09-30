from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_resaas.saas.core.entitlements import snapshot
from django_resaas.saas.core.tenant.context import ResaasContextService


class EntitlementsAPIView(APIView):
    """PROTECTED. GET /api/resaas/entitlements/ - the features, capacities
    (limit + current usage) of the tenant in the signed RESAAS context, for the
    frontend's UX. It grants nothing: every operation is enforced server-side."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request, "tenant_context_error", None):
            error = request.tenant_context_error
            raise error if isinstance(error, PermissionDenied) else PermissionDenied(str(error))

        if not getattr(request, "tenant_context", None):
            raise PermissionDenied("RESAAS context is required.")

        ResaasContextService.validate_for_user(request.user, request.tenant_context)

        return Response(snapshot(request))
