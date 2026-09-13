"""
Address becomes a generic, reusable record (content_type/object_id)
instead of being tied to Entity/Branch via a dedicated OneToOneField
each - Branch now gets its address through AddressMixin (a Branch can
have MAIN/HOME/OFFICE/... addresses, not just one). Entity keeps its
own existing `address` OneToOneField untouched (out of scope here) -
only Branch's is being retired.

Backfills any already-linked Branch/Entity address into the new
content_type/object_id shape *before* dropping Branch.address, so no
existing address data is silently lost - safe no-op wherever nothing
was ever linked (confirmed empty in dev, but production may differ).
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_content_type_and_object_id(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Address = apps.get_model("django_resaas", "Address")
    Branch = apps.get_model("django_resaas", "Branch")
    Entity = apps.get_model("django_resaas", "Entity")

    branch_ct, _ = ContentType.objects.get_or_create(
        app_label="django_resaas", model="branch",
    )
    entity_ct, _ = ContentType.objects.get_or_create(
        app_label="django_resaas", model="entity",
    )

    for branch in Branch.objects.exclude(address_id__isnull=True):
        Address.objects.filter(id=branch.address_id).update(
            content_type_id=branch_ct.id,
            object_id=str(branch.id),
            address_type="main",
        )

    for entity in Entity.objects.exclude(address_id__isnull=True):
        Address.objects.filter(id=entity.address_id).update(
            content_type_id=entity_ct.id,
            object_id=str(entity.id),
            address_type="main",
        )

    # Any Address row still unlinked at this point (never referenced by
    # either OneToOneField) has no owner to infer - safe to drop rather
    # than leave it violating the new NOT NULL content_type below.
    Address.objects.filter(content_type_id__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("django_resaas", "0002_alter_animationsetting_button_animation_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="address",
            name="content_type",
            field=models.ForeignKey(
                to="contenttypes.contenttype",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="resaas_addresses",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="address",
            name="object_id",
            field=models.CharField(max_length=255, db_index=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="address",
            name="address_type",
            field=models.CharField(
                max_length=30,
                choices=[
                    ("main", "Principal"),
                    ("home", "Casa"),
                    ("office", "Escritório"),
                    ("billing", "Facturação"),
                    ("shipping", "Entrega"),
                    ("other", "Outro"),
                ],
                default="main",
                db_index=True,
            ),
        ),
        migrations.RunPython(
            backfill_content_type_and_object_id,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="address",
            name="content_type",
            field=models.ForeignKey(
                to="contenttypes.contenttype",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="resaas_addresses",
                null=False,
            ),
        ),
        migrations.RemoveField(
            model_name="branch",
            name="address",
        ),
        migrations.AddConstraint(
            model_name="address",
            constraint=models.UniqueConstraint(
                fields=["content_type", "object_id", "address_type"],
                name="unique_address_type_per_object",
            ),
        ),
        migrations.AddIndex(
            model_name="address",
            index=models.Index(
                fields=["content_type", "object_id"],
                name="django_resa_content_cf551a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="address",
            index=models.Index(
                fields=["content_type", "object_id", "address_type"],
                name="django_resa_content_c31238_idx",
            ),
        ),
    ]
