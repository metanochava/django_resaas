from rest_framework import status, generics
from rest_framework.response import Response

from django_saas.core.utils.translate import Translate
from django_saas.data.user.serializers.me import MeSerializer


class MeAPIView(generics.GenericAPIView):
    serializer_class = MeSerializer

    def get(self, request):
        serializer = self.serializer_class(
            request.user,
            context={'request': request}
        )
        data = serializer.data.copy()
        return Response( data, status=status.HTTP_200_OK)
