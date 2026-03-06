from rest_framework import generics, status
from rest_framework.response import Response


from django_saas.data.user.serializers.set_new_password import SetNewPasswordSerializer


class SetNewPasswordAPIView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def patch(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {
                'alert_success': True,
                'message': 'Senha redefinida com sucesso'
            },
            status=status.HTTP_200_OK
        )
