from django.contrib import auth

from rest_framework import generics, status
from rest_framework.response import Response

from django_saas.core.utils.translate import Translate
from django_saas.models.user import User
from django_saas.data.user.serializers.login import LoginSerializer


class ChangePasswordEmailAPIView(generics.GenericAPIView):
    def post(self, request):
        user = auth.authenticate(
            email=request.data.get('email'),
            password=request.data.get('password')
        )

        if not user:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'A senha atual está incorreta'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(request.data.get('passwordNova', '')) < 8:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'A senha deve ter no mínimo 8 caracteres'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.get(id=user.id)
        user.set_password(request.data.get('passwordNova'))
        user.save()

        return Response(
            {
                'alert_success': Translate.tdc(
                    request,
                    'Senha alterada com sucesso'
                )
            },
            status=status.HTTP_202_ACCEPTED
        )


