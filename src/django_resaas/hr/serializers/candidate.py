# hr/serializers/candidate.py

from django_resaas.saas.core.base.serializers import BaseSerializer

from django_resaas.hr.models.candidate import Candidate


class CandidateSerializer(BaseSerializer):

    class Meta:
        model = Candidate
        fields = "__all__"
