import base64

import pyotp

from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils.generate_key_otp import generateKeyOTP
from django_resaas.models.user import User


EXPIRY_TIME = 120  # seconds


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
                    'Do not share this code'
                ) + f':\nOTP {otp.now()}'
            )
        except Exception:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'Error sending the OTP'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                'alert_success': Translate.tdc(
                    request,
                    'We sent an OTP to your number'
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
                        'User not found'
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
                        'Authorized successfully'
                    )
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                'alert_error': Translate.tdc(
                    request,
                    'Invalid or expired OTP'
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )
