# hr/serializers/holiday.py

from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.holiday import Holiday


class HolidaySerializer(BaseSerializer):

    class Meta:
        model = Holiday
        fields = "__all__"
