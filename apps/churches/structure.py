"""One-off helpers that bring older data in line with the church's real organigram:

    Area > District > Station          (the National Headquarters is one particular station)
"""
from .models import Branch

HQ_STATION_NAME = "Ehi Road Station"


def convert_legacy_headquarters(out=print):
    """Older versions kept a separate top-level 'National Headquarters' unit above the areas.
    Lift the areas to the top level, move its councils to the HQ station (or make them general)
    and remove the empty placeholder."""
    old = list(Branch.objects.filter(level="hq"))
    if not old:
        return 0
    target = Branch.objects.filter(is_national_headquarters=True).first() or Branch.objects.filter(
        level=Branch.Level.STATION, name=HQ_STATION_NAME).first()
    from apps.leadership.models import Council

    for hq in old:
        Branch.objects.filter(parent=hq).update(parent=None)
        Council.objects.filter(branch=hq).update(branch=target)
        hq.delete()
        out(f"Removed the old top-level '{hq.name}' placeholder (areas now stand on their own).")
    return len(old)


def mark_national_headquarters(name=HQ_STATION_NAME, out=print):
    """Flag the church's National Headquarters station (Ehi Road Station, Aba South District)."""
    if Branch.objects.filter(is_national_headquarters=True).exists():
        return Branch.objects.get(is_national_headquarters=True)
    station = Branch.objects.filter(level=Branch.Level.STATION, name=name).first()
    if station:
        station.is_national_headquarters = True
        station.save(update_fields=["is_national_headquarters", "updated_at"])
        out(f"{name} is now marked as the National Headquarters.")
    return station


DEMO_SLUGS = ["central-branch", "central-district", "central-area", "headquarters"]


def remove_demo_units(out=print):
    """Delete the sample units that `seed_demo` used to create, so only the church's real structure remains."""
    n = 0
    for slug in DEMO_SLUGS:  # children first
        for b in Branch.objects.filter(slug=slug):
            if b.children.exists():
                continue
            out(f"Removed sample unit '{b.name}'.")
            b.delete()
            n += 1
    return n
