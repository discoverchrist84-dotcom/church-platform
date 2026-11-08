from django.core.management.base import BaseCommand
from django.db import transaction

from apps.churches.data.leaders import AREAS, DISTRICT_SUPERINTENDENTS
from apps.churches.models import Branch, BranchLeader

L = Branch.Level


def _set_superintendent(branch, name):
    """Make `name` the one current superintendent of `branch` (idempotent)."""
    current = BranchLeader.objects.filter(branch=branch, role=BranchLeader.Role.SUPERINTENDENT, is_current=True)
    if current.filter(name=name).exists():
        return False
    current.update(is_current=False)
    BranchLeader.objects.create(branch=branch, name=name, role=BranchLeader.Role.SUPERINTENDENT)
    return True


class Command(BaseCommand):
    help = "Create Areas 1-6 and set the Area and District superintendents (safe to run again)."

    @transaction.atomic
    def handle(self, *args, **opts):
        made = set_ = 0
        for i, (aname, supt) in enumerate(AREAS, start=1):
            area = Branch.objects.filter(level=L.AREA, name=aname).first()
            if not area:
                area = Branch.objects.create(name=aname, level=L.AREA, serial=i)
                made += 1
            if supt and _set_superintendent(area, supt):
                set_ += 1
        missing = []
        for dname, supt in DISTRICT_SUPERINTENDENTS:
            district = Branch.objects.filter(level=L.DISTRICT, name=dname).first()
            if not district:
                missing.append(dname)
                continue
            if _set_superintendent(district, supt):
                set_ += 1
        self.stdout.write(self.style.SUCCESS(f"Areas created: {made}. Superintendents set: {set_}."))
        if missing:
            self.stdout.write(f"Districts not found (run import_stations first?): {', '.join(missing)}")
