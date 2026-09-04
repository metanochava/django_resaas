# hr/views/onboarding_template.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.onboarding_template import OnboardingTemplate
from django_resaas.hr.serializers.onboarding_template import OnboardingTemplateSerializer


@registerView('onboardingtemplates', module='hr')
class OnboardingTemplateAPIView(BaseAPIView):
    queryset = OnboardingTemplate.objects.all()
    serializer_class = OnboardingTemplateSerializer
