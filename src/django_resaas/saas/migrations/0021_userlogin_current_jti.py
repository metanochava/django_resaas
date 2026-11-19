from django.db import migrations, models


class Migration(migrations.Migration):
    """The session's current refresh token (refresh rotation): additive, null on
    existing sessions (their current token stays token_jti)."""

    dependencies = [
        ("django_resaas", "0020_form_definitions"),
    ]

    operations = [
        migrations.AddField(
            model_name="userlogin",
            name="current_jti",
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
    ]
