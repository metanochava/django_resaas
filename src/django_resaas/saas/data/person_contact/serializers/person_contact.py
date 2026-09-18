from django_resaas.saas.models.person_contact import PersonContact
from django_resaas.saas.core.base.serializers import BaseSerializer


class PersonContactSerializer(BaseSerializer):

    class Meta:
        model = PersonContact
        fields = "__all__"
