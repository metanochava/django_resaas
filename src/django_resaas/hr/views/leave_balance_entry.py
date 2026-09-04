# hr/views/leave_balance_entry.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.leave_balance_entry import LeaveBalanceEntry
from django_resaas.hr.serializers.leave_balance_entry import LeaveBalanceEntrySerializer


@registerView('leavebalanceentries', module='hr')
class LeaveBalanceEntryAPIView(BaseAPIView):
    queryset = LeaveBalanceEntry.objects.all()
    serializer_class = LeaveBalanceEntrySerializer
