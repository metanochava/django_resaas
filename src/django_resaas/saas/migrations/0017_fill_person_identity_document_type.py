"""Person.identity_document_type for the people registered before it existed
(0015): the type of the person's first document - one with a number first.
Only people without a type and with documents are touched; nothing is
invented for the others (the patient form asks for one on the next save).
Idempotent; the reverse does nothing."""
from django.db import migrations


def fill_identity_document_type(apps, schema_editor):
    Person = apps.get_model("django_resaas", "Person")
    Document = apps.get_model("django_resaas", "Document")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.filter(app_label="django_resaas", model="person").first()
    if content_type is None:
        return

    documents = Document.objects.filter(content_type=content_type, tipo__isnull=False)
    if any(f.name == "deleted_at" for f in Document._meta.get_fields()):
        documents = documents.filter(deleted_at__isnull=True)

    first_type = {}
    # documents with a number first, then the oldest
    for person_id, tipo_id, numero in documents.order_by("created_at").values_list("object_id", "tipo_id", "numero"):
        has_number = bool((numero or "").strip())
        current = first_type.get(person_id)
        if current is None or (has_number and not current[1]):
            first_type[person_id] = (tipo_id, has_number)

    people = Person.objects.filter(id__in=list(first_type), identity_document_type__isnull=True)
    for person in people.only("id"):
        Person.objects.filter(id=person.id).update(identity_document_type_id=first_type[person.id][0])


class Migration(migrations.Migration):

    dependencies = [
        ("django_resaas", "0016_document_issued_by"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(fill_identity_document_type, migrations.RunPython.noop),
    ]
