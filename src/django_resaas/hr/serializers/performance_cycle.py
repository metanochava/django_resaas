# hr/serializers/performance_cycle.py

from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.performance_cycle import PerformanceCycle


class PerformanceCycleSerializer(BaseSerializer):

    class Meta:
        model = PerformanceCycle
        fields = "__all__"
