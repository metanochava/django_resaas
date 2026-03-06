import re

from rest_framework import generics, status
from rest_framework.response import Response

from django_saas.core.utils.translate import Translate
from django_saas.models.user_login import UserLogin
from django_saas.data.user.serializers.login import LoginSerializer
from django.contrib.auth import authenticate

class LoginAPIView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        data = request.data.copy()  # ✅ agora é mutável
        identifier = data.get("identifier")
        password = data.get("password")
        data['id'] = identifier
        

        # 🔐 validações defensivas
        if not isinstance(identifier, str) or not isinstance(password, str):
            return Response(
                {"alert_error": "Credenciais inválidas"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 🔐 validação defensiva mínima

        serializer = self.serializer_class(
            data=data,
            context={'request': request}
        )


        serializer.is_valid(raise_exception=True)


        # data['user'] = serializer.data['id']

        


        # user_login = LoginSerializer(data=data)
        # user_login.is_valid(raise_exception=True)
        # user_login.save()
        
        response = serializer.data.copy()   # ← dados do serializer

        return Response(
            response,
            status=status.HTTP_200_OK,
        )
