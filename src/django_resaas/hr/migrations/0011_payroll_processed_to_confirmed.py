from django.db import migrations


def processed_to_confirmed(apps, schema_editor):
    """The old Payroll.status choices were draft/processed/paid/cancelled;
    Fase 8 introduces a 6-state machine (draft/calculated/reviewed/
    confirmed/paid/cancelled) with no 'processed' value. Any row still
    carrying the old 'processed' value is remapped to the closest
    equivalent - 'confirmed' (a row that had already been through payroll
    processing, same semantic position in the old lifecycle just before
    'paid') - so no historical data silently becomes an invalid/unknown
    status string."""
    Payroll = apps.get_model("hr", "Payroll")
    Payroll.objects.filter(status="processed").update(status="confirmed")


def confirmed_to_processed(apps, schema_editor):
    Payroll = apps.get_model("hr", "Payroll")
    Payroll.objects.filter(status="confirmed").update(status="processed")


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0010_payroll_calculated_at_payroll_confirmed_at_and_more"),
    ]

    operations = [
        migrations.RunPython(processed_to_confirmed, confirmed_to_processed),
    ]
