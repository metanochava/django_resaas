from django_resaas.saas.models.person_contact import PersonContact
from django_resaas.saas.core.base.views import BaseAPIView, registerView

from django_resaas.saas.data.person_contact.serializers.person_contact import (
    PersonContactSerializer,
)


@registerView('personcontacts')
class PersonContactAPIView(BaseAPIView):
    serializer_class = PersonContactSerializer
    queryset = PersonContact.objects.all()
    lookup_field = "id"
