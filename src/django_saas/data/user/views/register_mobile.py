import base64
from datetime import datetime

import pyotp

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_saas.core.utils.translate import Translate
from django_saas.core.utils.username import UserName

from django_saas.models.user import User
from django_saas.models.pessoa import Pessoa

from django_saas.data.user.serializers.register import RegisterSerializer





class RegisterMobileAPIView(APIView):

    @staticmethod
    def post(request):
        phone = str('+' + request.data['mobile']).replace('+', '')

        try:
            user = User.objects.get(mobile=phone)
        except ObjectDoesNotExist:
            if 'reset_senha' in request.query_params:
                return Response(
                    {
                        'alert_error': Translate.tdc(
                            request,
                            'O número não existe'
                        ) + f' <br><b>{phone}</b>'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            nome = (
                request.META['HTTP_ORIGIN']
                .split('.')[0]
                .upper()
                .split('/')[-1]
            )

            request.data['username'] = UserName.Create(
                request.data['username'].replace(' ', '_')
            )
            request.data['mobile'] = phone
            request.data['email'] = None

            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            user = User.objects.get(mobile=phone)

            pessoa = Pessoa(user=user)
            pessoa.save()

        user.counter += 1
        user.save()

        keygen = generateKeyOTP()
        key = base64.b32encode(keygen.returnValue(phone).encode())
        otp = pyotp.HOTP(key)

        try:
            SMS.send(
                from__='+17244014353',
                to__='+258' + phone,
                text__=Translate.tdc(
                    request,
                    'Não partilhe este código'
                ) + f':\nOTP {otp.at(user.counter)}'
            )
        except Exception as exc:
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
                ) + f' <br><b>{phone}</b>',
                'data': {'otp': otp.at(user.counter)},
            },
            status=status.HTTP_201_CREATED
        )

    @staticmethod
    def put(request):
        phone = str('+' + request.data['mobile']).replace('+', '')

        try:
            user = User.objects.get(mobile=phone)
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
        otp = pyotp.HOTP(key)

        if otp.verify(request.data['otp'], user.counter):
            user.is_verified_mobile = True
            user.save()

            return Response(
                {
                    'alert_success': Translate.tdc(
                        request,
                        'Autorizado com sucesso'
                    ),
                    'data': {
                        'id': user.id,
                        'otp': request.data['otp'],
                        'mobile': request.data['mobile'],
                    },
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
