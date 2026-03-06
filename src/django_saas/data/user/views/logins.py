from rest_framework import generics, status, permissions
from rest_framework.response import Response

from django_saas.core.utils.translate import Translate
from django_saas.models.user_login import UserLogin
from django_saas.data.user.serializers.login import LoginSerializer


class LoginsAPIView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user_login = UserLogin.objects.filter(
            user=request.user
        ).order_by('data', '-hora')

        user_logins = LoginSerializer(
            user_login,
            many=True
        )

        return Response(
            {
                'alert_success': Translate.tdc(
                    request,
                    'Histórico de logins carregado com sucesso'
                ),
                'data': user_logins.data
            },
            status=status.HTTP_200_OK
        )

