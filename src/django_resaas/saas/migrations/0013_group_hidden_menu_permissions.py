from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_resaas", "0012_group_hidden_menu_apps"),
    ]

    operations = [
        migrations.AddField(
            model_name="group",
            name="hidden_menu_permissions",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
