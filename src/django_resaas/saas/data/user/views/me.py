from rest_framework import status, generics, permissions
from rest_framework.response import Response

from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.data.user.serializers.me import MeSerializer


class MeAPIView(generics.GenericAPIView):
    # PROTECTED: the signed-in account's own profile
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MeSerializer

    def get(self, request):
        serializer = self.serializer_class(
            request.user,
            context={'request': request}
        )
        data = serializer.data.copy()
        return Response( data, status=status.HTTP_200_OK)
