from rest_framework import status, generics
from rest_framework.response import Response

from django_resaas.core.utils.translate import Translate

from rest_framework.views import APIView
from rest_framework import status

from django_resaas.data.user.serializers.me import MeSerializer


class MeAPIView(APIView):

    def get(self, request, *args, **kwargs):

        if not request.user.is_authenticated:

            return Response(
                {
                    "detail": "Não autenticado"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = MeSerializer(
            request.user,
            context={
                "request": request
            }
        )

        data = serializer.data.copy()

        return Response(data)