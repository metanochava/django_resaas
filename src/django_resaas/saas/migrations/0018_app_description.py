from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_resaas", "0017_fill_person_identity_document_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="app",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
    ]
