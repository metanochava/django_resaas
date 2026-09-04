from django_resaas.engine.management.commands.resaas_doctor import (
    Command as ResaasDoctorCommand,
)


class Command(ResaasDoctorCommand):
    """`resaas_check` and `resaas_doctor` were both asked for as distinct
    names in the original design (`resaas_check` for structural validation,
    `resaas_doctor` for the broader diagnostic), but once every check
    lived in one small, extensible registry (core/doctor/), there was no
    actual behavioral split left to preserve - both would run the exact
    same checks with the exact same output. Kept as a real alias (a
    subclass, not a copy-pasted file) rather than inventing an artificial
    difference between the two."""

    help = (
        "Alias for `resaas_doctor` - structural validation of a RESAAS "
        "installation (database, migrations, views, schema, actions, "
        "permissions, modules). Same checks, same output, same exit codes."
    )
