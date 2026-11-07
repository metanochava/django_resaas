from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_resaas", "0010_sso_authorization_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="userlogin",
            name="sso_family",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
    ]
