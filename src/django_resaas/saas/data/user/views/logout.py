from rest_framework import generics, status, permissions
from rest_framework.response import Response

from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.data.user.serializers.logout import LogoutSerializer
from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin


class LogoutAPIView(ResaasResponseMixin, generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        from django_resaas.saas.core.services import refresh_cookie

        # the refresh token of the body, else of the HttpOnly cookie
        refresh = request.data.get("refresh") or refresh_cookie.read(request)
        serializer = self.serializer_class(data={"refresh": refresh}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response = Response(
            {
                'alert_success': Translate.tdc(
                    request,
                    'Logout successful'
                )
            },
            status=status.HTTP_200_OK
        )
        refresh_cookie.clear(response)
        return response
