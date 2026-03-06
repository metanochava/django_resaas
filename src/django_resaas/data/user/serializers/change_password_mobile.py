import base64

from rest_framework import generics, status
from rest_framework.response import Response

import pyotp

from .models import User
from .serializers import ResetPasswordEmailRequestSerializer
from .classes.translate import Translate
from .utils.generateKeyOTP import generateKeyOTP




class ChangePasswordMobileAPIView(generics.GenericAPIView):
    def post(self, request):
        phone = request.data.get('mobile')
        user = User.objects.get(mobile=phone)

        keygen = generateKeyOTP()
        key = base64.b32encode(
            keygen.returnValue(phone).encode()
        )
        otp = pyotp.HOTP(key)

        if otp.verify(request.data.get("otp"), user.counter):
            user.set_password(request.data.get('password'))
            user.save()
            return Response(
                {
                    'alert_success': Translate.tdc(
                        request,
                        'Senha redefinida com sucesso'
                    )
                },
                status=status.HTTP_202_ACCEPTED
            )

        return Response(
            {
                'alert_error': Translate.tdc(
                    request,
                    'OTP inválido ou expirado'
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )
