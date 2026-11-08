from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_resaas", "0011_userlogin_sso_family"),
    ]

    operations = [
        migrations.AddField(
            model_name="group",
            name="hidden_menu_apps",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
