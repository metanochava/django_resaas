"""Load the public site content of entity types (EntityType.site) and its
translations (Translation rows) from a JSON file.

    python manage.py load_entity_type_sites path/to/entity_type_sites.json
    python manage.py load_entity_type_sites file.json --dry-run

File:

    {
      "sites": {"Saude": {"layout": "orbit", "hero": {...}, "features": {...}, ...}, ...},
      "themes": {"Saude": {"primary": "#0E7C86", "secondary": "#2563EB", "accent": "#F97362"}, ...},
      "translations": {"pt-pt": {"Canonical English": "Português", ...},
                       "es-es": {...}, "fr-fr": {...}}
    }

Idempotent: a type's site is replaced by the file's (types are matched by
name, ignoring case; a type missing from the database is reported and
skipped); the colours in "themes" are written to the type's Theme (only
fields that exist on Theme are accepted). A Theme that is also used by
another entity type, an Entity or a User is never changed: the type gets its
own copy first, so nobody else's colours move. A translation is created or
updated by (language, key). The
translation caches of the languages touched are cleared, so the frontend
gets the new texts on its next load. Installation data: nothing is loaded
by migrations.
"""
import json

from django.core.cache import cache
from django.forms.models import model_to_dict
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.language import Language
from django_resaas.saas.models.theme import Theme
from django_resaas.saas.models.theme_surface import ThemeSurface
from django_resaas.saas.models.translation import Translation


class Command(BaseCommand):
    help = "Load EntityType.site content and its translations from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("file", help="JSON file with 'sites' and 'translations'.")
        parser.add_argument("--dry-run", action="store_true", help="Validate and report, change nothing.")

    def handle(self, *args, **options):
        data = self._read(options["file"])
        sites = data.get("sites") or {}
        themes = data.get("themes") or {}
        translations = data.get("translations") or {}
        if not all(isinstance(part, dict) for part in (sites, themes, translations)):
            raise CommandError("'sites', 'themes' and 'translations' must be objects.")

        report = {"sites": 0, "themes": 0, "missing_types": [], "translations_created": 0, "translations_updated": 0}

        with transaction.atomic():
            for name, content in sites.items():
                if not isinstance(content, dict):
                    raise CommandError(f"The site of '{name}' must be an object.")
                entity_type = EntityType.objects.filter(name__iexact=name).first()
                if entity_type is None:
                    report["missing_types"].append(name)
                    continue
                entity_type.site = content
                entity_type.save(update_fields=["site", "updated_at"])
                report["sites"] += 1

            for name, colours in themes.items():
                entity_type = EntityType.objects.filter(name__iexact=name).first()
                if entity_type is None:
                    if name not in report["missing_types"]:
                        report["missing_types"].append(name)
                    continue
                self._apply_theme(entity_type, name, colours)
                report["themes"] += 1

            touched = []
            for code, items in translations.items():
                language = Language.objects.filter(code__iexact=code).first()
                if language is None:
                    raise CommandError(f"Unknown language code '{code}'.")
                if not isinstance(items, dict):
                    raise CommandError(f"The translations of '{code}' must be an object.")
                touched.append(language.code)
                for key, value in items.items():
                    row = Translation.objects.filter(language=language, chave=key).first()
                    if row is None:
                        Translation.objects.create(language=language, chave=key, translation=value)
                        report["translations_created"] += 1
                    elif row.translation != value:
                        row.translation = value
                        row.save(update_fields=["translation", "updated_at"])
                        report["translations_updated"] += 1

            if options["dry_run"]:
                transaction.set_rollback(True)

        if not options["dry_run"]:
            for code in touched:
                key = f"translation:{str(code).lower().replace('-', '')}"
                cache.delete_many([key, f"{key}:folded"])

        prefix = "[dry-run] " if options["dry_run"] else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}sites: {report['sites']}, themes: {report['themes']}, translations created: {report['translations_created']}, "
            f"updated: {report['translations_updated']}"
        ))
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
