from rest_framework import generics, status, permissions
from rest_framework.response import Response

from django_saas.core.utils.translate import Translate
from django_saas.data.user.serializers.logout import LogoutSerializer


class LogoutAPIView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                'alert_success': Translate.tdc(
                    request,
                    'Logout efectuado com sucesso'
                )
            },
            status=status.HTTP_200_OK
        )
