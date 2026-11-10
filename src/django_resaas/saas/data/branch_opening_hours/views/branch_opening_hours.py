from django_resaas.saas.core.base.views import BaseAPIView, registerView
from django_resaas.saas.data.branch_opening_hours.serializers.branch_opening_hours import BranchOpeningHoursSerializer
from django_resaas.saas.models.branch_opening_hours import BranchOpeningHours


@registerView('branchopeninghours')
class BranchOpeningHoursAPIView(BaseAPIView):
    """A branch's opening hours (?branch=<id>). The rows carry no entity of
    their own: they are this Entity's through their branch."""
    serializer_class = BranchOpeningHoursSerializer
    queryset = BranchOpeningHours.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(branch__entity_id=self.request.entity_id)
