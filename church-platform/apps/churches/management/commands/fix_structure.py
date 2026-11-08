from django.core.management.base import BaseCommand

from apps.churches.structure import convert_legacy_headquarters, mark_national_headquarters, remove_demo_units


class Command(BaseCommand):
    help = "Bring older data in line: areas become top level and Ehi Road Station is the National Headquarters."

    def handle(self, *args, **opts):
        convert_legacy_headquarters(self.stdout.write)
        remove_demo_units(self.stdout.write)
        mark_national_headquarters(out=self.stdout.write)
        self.stdout.write(self.style.SUCCESS("Structure is up to date."))
