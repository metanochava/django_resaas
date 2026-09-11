# hr/serializers/competency.py

from django_resaas.saas.core.base.serializers import BaseSerializer

from django_resaas.hr.models.competency import Competency


class CompetencySerializer(BaseSerializer):

    class Meta:
        model = Competency
        fields = "__all__"
