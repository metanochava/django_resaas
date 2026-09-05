# hr/views/disciplinary_action.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.disciplinary_action import DisciplinaryAction
from django_resaas.hr.serializers.disciplinary_action import DisciplinaryActionSerializer
from django_resaas.hr.services import lifecycle_service


@registerView('disciplinaryactions', module='hr')
class DisciplinaryActionAPIView(BaseAPIView):
    """As sensitive as its parent DisciplinaryCase (pedido secção 41) -
    gated by its own dedicated permissions."""

    queryset = DisciplinaryAction.objects.all()
    serializer_class = DisciplinaryActionSerializer

    def perform_create(self, serializer):
        super().perform_create(serializer)
        action = serializer.instance
        lifecycle_service.issue_disciplinary_action(
            action.case, action, actor=self.request.user
        )
