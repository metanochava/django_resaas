# Theme ownership: a theme without owner is a template; a customized copy
# belongs to one EntityType, Entity or User (ThemeAPIView.customize).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_resaas", "0006_entity_type_site"),
    ]

    operations = [
        migrations.AddField(
            model_name="theme",
            name="owner_entity_type",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name="owned_themes", to="django_resaas.entitytype",
                help_text="Entity type this customized theme belongs to.",
            ),
        ),
        migrations.AddField(
            model_name="theme",
            name="owner_entity",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name="owned_themes", to="django_resaas.entity",
                help_text="Entity this customized theme belongs to.",
            ),
        ),
        migrations.AddField(
            model_name="theme",
            name="owner_user",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name="owned_themes", to="django_resaas.user",
                help_text="User this customized theme belongs to.",
            ),
        ),
    ]
