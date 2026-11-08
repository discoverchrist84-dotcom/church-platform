from django.core.management.base import BaseCommand
from django.db import transaction

from apps.churches.data.leaders import AREA_DISTRICTS, AREAS
from apps.churches.data.stations import COUNTRY, DISTRICTS, MOVED, PENDING, RENAMED_DISTRICTS
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
        # Areas 1-6 (district -> Area comes from data/leaders.py); anything unlisted goes to `area`.
        areas = {}
        for i, (aname, _supt) in enumerate(AREAS, start=1):
            obj = Branch.objects.filter(level=L.AREA, name=aname).first() or Branch.objects.create(
                name=aname, level=L.AREA, serial=i)
            areas[aname] = obj
        area_of = {d: areas[a] for a, ds in AREA_DISTRICTS.items() for d in ds}
        fallback = None
        for old, new in RENAMED_DISTRICTS.items():
            o = Branch.objects.filter(level=L.DISTRICT, name=old).first()
            if o and not Branch.objects.filter(level=L.DISTRICT, name=new).exists():
                o.name = new
                o.slug = ""  # new slug follows the new name
                o.save()
        nd = ns = 0
        sn = 0
        for di, (dname, stations) in enumerate(DISTRICTS, start=1):
            parent_area = area_of.get(dname)
            if parent_area is None:
                fallback = fallback or Branch.objects.filter(level=L.AREA, name=area).first() or Branch.objects.create(
                    name=area, level=L.AREA, description="Temporary home for districts until their Area is set.")
                parent_area = fallback
            district = Branch.objects.filter(level=L.DISTRICT, name=dname).first()
            if not district:
                district = Branch.objects.create(name=dname, level=L.DISTRICT, parent=parent_area, serial=di)
                nd += 1
            else:
                Branch.objects.filter(pk=district.pk).update(serial=di, parent=parent_area)
            for item in stations:
                sname, addr = item[0], item[1]
                sn = item[2] if len(item) > 2 else sn + 1  # the station's S/N in the printed register
                existing = Branch.objects.filter(level=L.STATION, name=sname, parent=district)
                if not existing.exists() and sname in MOVED:
                    moved = Branch.objects.filter(level=L.STATION, name=sname, parent__name__in=MOVED[sname])
                    moved.update(parent=district)
                    existing = Branch.objects.filter(level=L.STATION, name=sname, parent=district)
                if existing.exists():
                    existing.update(serial=sn)
                    continue
                country = COUNTRY.get(addr, "Nigeria")
                Branch.objects.create(name=sname, level=L.STATION, parent=district, address=addr, serial=sn,
                                      city=addr.split(",")[-1].strip() if addr else "", country=country)
                ns += 1
        leftover = Branch.objects.filter(level=L.AREA, name=area).first()
        if leftover and not leftover.children.exists():
            leftover.delete()
        convert_legacy_headquarters(self.stdout.write)
        remove_demo_units(self.stdout.write)
        mark_national_headquarters(out=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(f"Added {nd} districts and {ns} stations in Areas 1-6."))
        for why, names in PENDING.items():
            self.stdout.write(f"Not imported ({why}): {', '.join(names)}")
