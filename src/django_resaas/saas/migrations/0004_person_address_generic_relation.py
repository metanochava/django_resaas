"""
Person adopts AddressMixin (generic content_type/object_id relation),
same move Branch already made in 0003. Person.address was a plain
ForeignKey (not OneToOne - related_name='persons' is plural, so
multiple Persons could historically share one Address row) which,
left in place, would silently shadow AddressMixin.address's own
property of the same name.

Backfills before dropping the column: the first Person referencing a
given Address takes over that row via the new generic relation: any
additional Person sharing the same Address gets its own copy, since
the new model ties one Address row to exactly one owner
(content_type+object_id are columns on the row itself, not a shared
foreign key) - no address data is lost, just no longer shared.
"""
from django.db import migrations, models
import django.db.models.deletion


def backfill_person_addresses(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Address = apps.get_model("django_resaas", "Address")
    Person = apps.get_model("django_resaas", "Person")

    person_ct, _ = ContentType.objects.get_or_create(
        app_label="django_resaas", model="person",
    )

    claimed_address_ids = set()

    for person in Person.objects.exclude(address_id__isnull=True):
        if person.address_id not in claimed_address_ids:
            Address.objects.filter(id=person.address_id).update(
                content_type_id=person_ct.id,
                object_id=str(person.id),
                address_type="main",
            )
            claimed_address_ids.add(person.address_id)
        else:
            # Another Person already claimed this exact Address row -
            # clone it so this Person keeps the same data as its own.
            original = Address.objects.get(id=person.address_id)
            clone_fields = {
                f.name: getattr(original, f.name)
                for f in Address._meta.fields
                if f.name not in ("id", "content_type", "object_id", "address_type")
            }
            Address.objects.create(
                content_type_id=person_ct.id,
                object_id=str(person.id),
                address_type="main",
                **clone_fields,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("django_resaas", "0003_address_generic_relation"),
    ]

    operations = [
        migrations.RunPython(
            backfill_person_addresses,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="person",
            name="address",
        ),
    ]
