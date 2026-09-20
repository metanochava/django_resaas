from rest_framework import generics, permissions, status
from rest_framework.response import Response

from django_resaas.saas.models.user_login import UserLogin

LIMIT = 30


class LoginsAPIView(generics.GenericAPIView):
    """GET logins/ - the signed-in user's OWN recent sign-ins (newest first).
    Own data only: authenticated, no other user's history is ever reachable."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        logins = UserLogin.objects.filter(user=request.user).order_by("-created_at")[:LIMIT]

        return Response(
            {"data": [{"device": login.dispositivo or "", "created_at": login.created_at} for login in logins]},
            status=status.HTTP_200_OK,
        )
