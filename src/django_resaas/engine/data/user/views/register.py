import json
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.serializers.json import DjangoJSONEncoder

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from django_resaas.engine.core.utils.translate import Translate
from django_resaas.engine.core.utils.username import UserName
from django_resaas.engine.core.utils.templates import render_email_template
from django_resaas.engine.core.utils.full_path import FullPath

from django_resaas.engine.models.user import User

from django_resaas.engine.data.user.serializers.register import RegisterSerializer



class RegisterAPIView(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request):
        origin = request.META.get(
            'HTTP_ORIGIN',
            'http://mytech.co.mz'
        )
        name = origin.split('.')[0].upper().split('/')[-1]

        data = request.data.copy()
        data['username'] = UserName.Create(
            request.data['username'].replace(' ', '_')
        )
        data['mobile'] = None

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        user = User.objects.get(email=serializer.data['email'])

        logo = FullPath.url(
            None,
            user.entity_type.icon.name
        )

        token = RefreshToken.for_user(user).access_token

        html_message = render_email_template(
            'REGISTER_CONFIRM',
            {
                'username': user.username,
                'token': str(token),
                'entity': name,
                'logo': logo,
                'origem': origin,
            }
        )

        mail = EmailMultiAlternatives(
            subject=f'{Translate.tdc(request, "Welcome")} {name}',
            body='',
            to=[user.email],
        )
        mail.attach_alternative(html_message, 'text/html')

        try:
            mail.send()
        except Exception:
            user.delete()
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'Error sending the email'
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                'alert_success': Translate.tdc(
                    request,
                    'Account created successfully'
                ),
                'data': json.loads(
                    json.dumps(
                        serializer.data,
                        cls=DjangoJSONEncoder
                    )
                ),
            },
            status=status.HTTP_201_CREATED
        )
