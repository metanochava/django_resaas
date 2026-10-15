"""Load the theme colours of entity types from a JSON file.

    python manage.py load_entity_type_themes path/to/entity_type_themes.json
    python manage.py load_entity_type_themes file.json --dry-run

File:

    {"themes": {"Saude": {"primary": "#0E7C86", "secondary": "#2563EB", "accent": "#F97362"}, ...}}

Idempotent: the colours are written to the type's Theme (types are matched by
name, ignoring case; a type missing from the database is reported and
skipped; only fields that exist on Theme are accepted). A Theme that is also
used by another entity type, an Entity or a User is never changed: the type
gets its own copy first, so nobody else's colours move. Installation data:
nothing is loaded by migrations.

The content of the public site at '/' is not data: the application registers
it in code (quasar_resaas registerEntityTypeSiteContent) and its translations
live in the static lang files. A file with "sites" or "translations" is
refused.
"""
import json

from django.forms.models import model_to_dict
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.theme import Theme
from django_resaas.saas.models.theme_surface import ThemeSurface


class Command(BaseCommand):
    help = "Load the theme colours of entity types from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("file", help="JSON file with 'themes'.")
        parser.add_argument("--dry-run", action="store_true", help="Validate and report, change nothing.")

    def handle(self, *args, **options):
        data = self._read(options["file"])
        retired = sorted(set(data) & {"sites", "translations"})
        if retired:
            raise CommandError(
                f"{', '.join(retired)}: the site content is code of the application "
                "(registerEntityTypeSiteContent) and its translations live in the static lang files."
            )
        themes = data.get("themes") or {}
        if not isinstance(themes, dict):
            raise CommandError("'themes' must be an object.")

        report = {"themes": 0, "missing_types": []}

        with transaction.atomic():
            for name, colours in themes.items():
                entity_type = EntityType.objects.filter(name__iexact=name).first()
                if entity_type is None:
                    report["missing_types"].append(name)
                    continue
                self._apply_theme(entity_type, name, colours)
                report["themes"] += 1

            if options["dry_run"]:
                transaction.set_rollback(True)

        prefix = "[dry-run] " if options["dry_run"] else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}themes: {report['themes']}"))
        if report["missing_types"]:
            self.stdout.write(self.style.WARNING(
                "Entity types not found (skipped): " + ", ".join(report["missing_types"])
            ))

    THEME_LOCKED_FIELDS = {"id", "name", "created_at", "updated_at", "deleted_at", "state", "created_by", "updated_by"}

    def _apply_theme(self, entity_type, name, colours):
        if not isinstance(colours, dict):
            raise CommandError(f"The theme of '{name}' must be an object.")
        fields = {field.name for field in Theme._meta.concrete_fields} - self.THEME_LOCKED_FIELDS
        unknown = sorted(set(colours) - fields)
        if unknown:
            raise CommandError(f"Unknown theme fields for '{name}': {', '.join(unknown)}")

        theme = entity_type.theme
        if theme is None or self._theme_is_shared(theme, entity_type):
            base = model_to_dict(theme, fields=fields) if theme else {}
            theme = Theme(name=entity_type.name, **base)

        changed = [key for key, value in colours.items() if getattr(theme, key) != value]
        for key in changed:
            setattr(theme, key, colours[key])
        if theme._state.adding:
            theme.save()
            entity_type.theme = theme
            entity_type.save(update_fields=["theme", "updated_at"])
        elif changed:
            theme.save(update_fields=changed + ["updated_at"])

    @staticmethod
    def _theme_is_shared(theme, entity_type):
        """Used by anything but this entity type (another type, an Entity, a
        User). The theme's own surfaces (ThemeSurface) are part of it, not users."""
        for relation in Theme._meta.related_objects:
            if not (relation.one_to_many or relation.one_to_one) or relation.related_model is ThemeSurface:
                continue
            queryset = relation.related_model._base_manager.filter(**{relation.field.name: theme})
            if relation.related_model is EntityType:
                queryset = queryset.exclude(pk=entity_type.pk)
            if queryset.exists():
                return True
        return False

    @staticmethod
    def _read(path):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except OSError as error:
            raise CommandError(f"Cannot read {path}: {error}")
        except json.JSONDecodeError as error:
            raise CommandError(f"Invalid JSON in {path}: {error}")
        if not isinstance(data, dict):
            raise CommandError("The file must hold a JSON object.")
        return data
