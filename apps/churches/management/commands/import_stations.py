from django.core.management.base import BaseCommand
from django.db import transaction

from apps.churches.data.stations import COUNTRY, DISTRICTS, PENDING
from apps.churches.models import Branch
from apps.churches.structure import convert_legacy_headquarters, mark_national_headquarters, remove_demo_units

L = Branch.Level


class Command(BaseCommand):
    help = "Import the church's districts and stations from the printed register (safe to run again)."

    def add_arguments(self, parser):
        parser.add_argument("--area", default="Unassigned Area",
                            help="Area to place the districts under (created if missing). Move districts later in the admin.")

    @transaction.atomic
    def handle(self, *args, area, **opts):
        area_obj = Branch.objects.filter(level=L.AREA, name=area).first() or Branch.objects.create(
            name=area, level=L.AREA, description="Temporary home for districts until their Area is set.")
        nd = ns = 0
        sn = 0
        for di, (dname, stations) in enumerate(DISTRICTS, start=1):
            district = Branch.objects.filter(level=L.DISTRICT, name=dname).first()
            if not district:
                district = Branch.objects.create(name=dname, level=L.DISTRICT, parent=area_obj, serial=di)
                nd += 1
            elif district.serial != di:
                Branch.objects.filter(pk=district.pk).update(serial=di)
            for sname, addr in stations:
                sn += 1  # the station's S/N in the printed register
                existing = Branch.objects.filter(level=L.STATION, name=sname, parent=district)
                if existing.exists():
                    existing.update(serial=sn)
                    continue
                country = COUNTRY.get(addr, "Nigeria")
                Branch.objects.create(name=sname, level=L.STATION, parent=district, address=addr, serial=sn,
                                      city=addr.split(",")[-1].strip() if addr else "", country=country)
                ns += 1
        convert_legacy_headquarters(self.stdout.write)
        remove_demo_units(self.stdout.write)
        mark_national_headquarters(out=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(f"Added {nd} districts and {ns} stations under '{area}'."))
        for why, names in PENDING.items():
            self.stdout.write(f"Not imported ({why}): {', '.join(names)}")
