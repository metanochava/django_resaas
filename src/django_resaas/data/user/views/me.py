from rest_framework import status, generics
from rest_framework.response import Response

from django_resaas.core.utils.translate import Translate
from django_resaas.data.user.serializers.me import MeSerializer

from rest_framework_simplejwt.authentication import JWTAuthentication


class MeAPIView(generics.GenericAPIView):

    serializer_class = MeSerializer

    def get(self, request, *args, **kwargs):

        print(
            "AUTHENTICATORS:",
            [
                type(auth).__name__
                for auth in self.get_authenticators()
            ]
        )

        print(
            "USER:",
            request.user
        )

        print(
            "AUTH:",
            request.auth
        )

        print(
            "AUTHORIZATION:",
            request.headers.get(
                "Authorization"
            )
        )

        return Response({})