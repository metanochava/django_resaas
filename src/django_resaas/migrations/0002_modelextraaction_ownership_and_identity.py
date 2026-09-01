from django.db import migrations, models


def delete_unidentifiable_rows(apps, schema_editor):
    """
    app/model/action are becoming NOT NULL - they're the row's whole
    logical identity (see the unique_model_extra_action constraint), so
    a row missing any of them was never addressable through the API or
    ActionSyncService in the first place. Safe to drop before the
    NOT NULL constraint is added; nothing legitimate can reference such
    a row by (app, model, action).
    """
    ModelExtraAction = apps.get_model("django_resaas", "ModelExtraAction")

    ModelExtraAction.objects.filter(
        models.Q(app__isnull=True)
        | models.Q(model__isnull=True)
        | models.Q(action__isnull=True)
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("django_resaas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            delete_unidentifiable_rows,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="modelextraaction",
            name="app",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="modelextraaction",
            name="model",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="modelextraaction",
            name="action",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="modelextraaction",
            name="managed_by",
            field=models.CharField(
                choices=[("decorator", "Decorator"), ("manual", "Manual")],
                default="manual",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="modelextraaction",
            name="permission_managed",
            field=models.BooleanField(default=False),
        ),
    ]
