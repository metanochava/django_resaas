"""manage.py seed_mobile_tabs [--entity-type NAME] [--replace]

Gives every Entity Type (or one) the phone tabs its active modules suggest
(<app>/mobile_tabs.py). Idempotent: an Entity Type that already has tabs
keeps them unless --replace."""
from django.core.management.base import BaseCommand, CommandError

from django_resaas.saas.core.services import mobile_tab_service
from django_resaas.saas.models.entity_type import EntityType


class Command(BaseCommand):
    help = "Give the Entity Types the phone tabs their modules suggest."

    def add_arguments(self, parser):
        parser.add_argument("--entity-type")
        parser.add_argument("--replace", action="store_true")

    def handle(self, *args, **opts):
        types = EntityType.objects.all()
        if opts["entity_type"]:
            types = types.filter(name=opts["entity_type"])
            if not types.exists():
                raise CommandError(f"Entity type not found: {opts['entity_type']}")
        for entity_type in types:
            made = mobile_tab_service.seed_entity_type(entity_type, replace=opts["replace"])
            self.stdout.write(f"{entity_type.name}: {made} tabs created")
