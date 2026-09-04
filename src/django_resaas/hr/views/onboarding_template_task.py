# hr/views/onboarding_template_task.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.onboarding_template_task import OnboardingTemplateTask
from django_resaas.hr.serializers.onboarding_template_task import (
    OnboardingTemplateTaskSerializer,
)


@registerView('onboardingtemplatetasks', module='hr')
class OnboardingTemplateTaskAPIView(BaseAPIView):
    queryset = OnboardingTemplateTask.objects.all()
    serializer_class = OnboardingTemplateTaskSerializer
