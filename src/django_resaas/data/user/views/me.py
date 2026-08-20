from rest_framework import status, generics
from rest_framework.response import Response

from django_resaas.core.utils.translate import Translate
from django_resaas.data.user.serializers.me import MeSerializer


class MeAPIView(generics.GenericAPIView):
    serializer_class = MeSerializer

    def get(self, request):
        print(
            "USER:",
            request.user
        )

        print(
            "AUTH:",
            request.auth
        )

        print(
            "IS_AUTHENTICATED:",
            request.user.is_authenticated
        )

        print(
            "AUTHORIZATION:",
            request.headers.get("Authorization")
        )

        print(
            "COOKIES:",
            request.COOKIES
        )

        print(request, request.user, "so para testar ")
        serializer = self.serializer_class(
            request.user,
            context={'request': request}
        )
        data = serializer.data.copy()
        return Response( data, status=status.HTTP_200_OK)
