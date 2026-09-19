"""
Person(+reuse)/Document/PersonContact creation shared by every intake flow
(add_employee today, add_paciente, future Student/Customer/...).

Deliberately NOT a full flow of its own: it has no idea what the caller is
registering the Person *as* (Employee, Paciente, ...). Each business module
wraps these helpers in its own @transaction.atomic service and adds the one
record it owns, so a failure anywhere never leaves a Person/Document/
PersonContact behind without the record the whole operation was for.
Duplicate detection itself lives in person_matching_service - this only
executes the choice the caller already made (reuse a Person, or create one).
"""
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.models.person import Person
from django_resaas.saas.data.person.serializers.person import PersonSerializer
from django_resaas.saas.data.person_contact.serializers.person_contact import PersonContactSerializer


class PersonRegistrationError(Exception):
    """Validation failure - `errors` mirrors DRF's own {field: [msgs]} shape."""

    def __init__(self, errors):
        self.errors = errors
        super().__init__("Person registration failed.")


def resolve_person(*, request, person_id=None, person_data=None, photo=None):
    """
    person_id: an existing Person chosen from person_matching_service's
        candidates - skips creation entirely (mutually exclusive with
        person_data).
    person_data: PersonSerializer-shaped dict for a genuinely new Person.
    photo: uploaded File for a NEW person's photo - applied as its own
        save() so PersonSerializer.create() never has to special-case a
        File among otherwise-plain fields.
    """
    if person_id:
        try:
            return Person.objects.select_for_update().get(id=person_id)
        except (Person.DoesNotExist, ValueError, TypeError):
            raise PersonRegistrationError({"person_id": [Translate.tdc(request, "Person not found.")]})

    serializer = PersonSerializer(data=person_data or {}, context={"request": request})

    if not serializer.is_valid():
        raise PersonRegistrationError({"person": serializer.errors})

    person = serializer.save(created_by=request.user, updated_by=request.user)

    if photo:
        person.photo = photo
        person.save(update_fields=["photo"])

    return person


def create_documents(*, request, person, documents):
    """
    documents: [{"tipo", "numero", "data_emissao", "data_validade",
        "arquivo": File|None}, ...] - only documents to CREATE. A reused
        Person's existing documents are never resent; a genuine duplicate
        (tipo, numero) still hits Document's own unique_together.
    """
    for doc in documents or []:
        person.documents.create(
            tipo_id=doc.get("tipo"),
            numero=doc.get("numero"),
            data_emissao=doc.get("data_emissao") or None,
            data_validade=doc.get("data_validade") or None,
            arquivo=doc.get("arquivo") or None,
            created_by=request.user,
            updated_by=request.user,
        )


def create_contacts(*, request, person, contacts):
    """contacts: [{...PersonContact fields...}, ...] - only NEW contacts."""
    for contact in contacts or []:
        serializer = PersonContactSerializer(
            data={**contact, "person": person.id},
            context={"request": request},
        )

        if not serializer.is_valid():
            raise PersonRegistrationError({"contacts": serializer.errors})

        serializer.save(created_by=request.user, updated_by=request.user)
