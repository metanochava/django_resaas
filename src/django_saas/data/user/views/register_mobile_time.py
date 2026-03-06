import base64
from datetime import datetime

import pyotp

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_saas.core.utils.translate import Translate
from django_saas.models.user import User


class generateKeyOTP:
    @staticmethod
    def returnValue(phone):
        return (
            str(phone)
            + str(datetime.date(datetime.now()))
            + settings.OTP_KEY
        )


EXPIRY_TIME = 120  # segundos


class RegisterMobileTimeAPIView(APIView):

    @staticmethod
    def get(request, phone):
        phone = '+' + str(phone).replace('+', '')

        try:
            mobile = User.objects.get(mobile=phone)
        except ObjectDoesNotExist:
            User.objects.create(mobile=phone)
            mobile = User.objects.get(mobile=phone)

        keygen = generateKeyOTP()
        key = base64.b32encode(keygen.returnValue(phone).encode())
        otp = pyotp.TOTP(key, interval=EXPIRY_TIME)

        try:
            SMS.send(
                from__='+13192205575',
                to__=phone,
                text__=Translate.tdc(
                    request,
                    'Não partilhe este código'
                ) + f':\nOTP {otp.now()}'
            )
        except Exception:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'Erro ao enviar o OTP'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                'alert_success': Translate.tdc(
                    request,
                    'Enviámos um OTP para o seu número'
                ),
                'data': {'otp': otp.now()}
            },
            status=status.HTTP_200_OK
        )

    @staticmethod
    def post(request, phone):
        phone = '+' + str(phone).replace('+', '')

        try:
            mobile = User.objects.get(mobile=phone)
        except ObjectDoesNotExist:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'Utilizador não encontrado'
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        keygen = generateKeyOTP()
        key = base64.b32encode(keygen.returnValue(phone).encode())
        otp = pyotp.TOTP(key, interval=EXPIRY_TIME)

        if otp.verify(request.data.get('otp')):
            mobile.isVerified = True
            mobile.save()
            return Response(
                {
                    'alert_success': Translate.tdc(
                        request,
                        'Autorizado com sucesso'
                    )
                },
                status=status.HTTP_200_OK
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
