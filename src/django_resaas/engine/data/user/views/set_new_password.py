from rest_framework import generics, status
from rest_framework.response import Response


from django_resaas.engine.data.user.serializers.set_new_password import SetNewPasswordSerializer


class SetNewPasswordAPIView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def patch(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                'alert_success': True,
                'message': 'Password reset successfully'
            },
            status=status.HTTP_200_OK
        )
