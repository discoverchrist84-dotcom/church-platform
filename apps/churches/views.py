from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.community.models import Announcement, Event
from apps.core.permissions import can_manage_branch
from apps.media_library.models import Sermon

from .models import Branch, BranchLeader, Membership
from .services import join_branch, leave_branch


LEVEL_RANK = {"region": 1, "district": 2, "local": 3}
PAGE_SIZE = 20


def _load_all():
    """Every active unit with its serving leaders attached, plus lookups for area/district/children.

    A church has hundreds of units at most, so we read them once and shape them in Python
    instead of running a query per row."""
    everything = list(
        Branch.objects.filter(is_active=True)
        .select_related("parent")
        .prefetch_related(Prefetch("leaders", queryset=BranchLeader.objects.filter(is_current=True), to_attr="current_leaders"))
    )
    by_id = {b.pk: b for b in everything}
    kids = {}
    for b in everything:
        kids.setdefault(b.parent_id, []).append(b)
    for b in everything:
        b.area_unit = b.district_unit = None
        node, guard = b, 0
        while node is not None and guard < 6:
            if node.level == Branch.Level.AREA and b.area_unit is None:
                b.area_unit = node
            if node.level == Branch.Level.DISTRICT and b.district_unit is None:
                b.district_unit = node
            node = by_id.get(node.parent_id)
            guard += 1
        b.child_count = len(kids.get(b.pk, []))
    return everything, kids


def _order(b):
    """Register order first (the church's own numbering), then alphabetical."""
    return (b.serial if b.serial is not None else 10**9, b.name.lower())


def _tree(everything, kids):
    def build(b):
        return (b, [build(c) for c in sorted(kids.get(b.pk, []), key=_order)])

    ids = {b.pk for b in everything}
    roots = sorted((b for b in everything if b.parent_id not in ids), key=lambda x: (LEVEL_RANK.get(x.level, 9), x.name.lower()))
    return [build(b) for b in roots]


SORTS = {
    "name": lambda b: b.name.lower(),
    "type": lambda b: (LEVEL_RANK.get(b.level, 9), b.name.lower()),
    "area": lambda b: ((b.area_unit.name.lower() if b.area_unit else "~"), LEVEL_RANK.get(b.level, 9), b.name.lower()),
    "district": lambda b: ((b.district_unit.name.lower() if b.district_unit else "~"), b.name.lower()),
    "leader": lambda b: ((b.superintendent.name.lower() if b.superintendent else "~"), b.name.lower()),
    "city": lambda b: ((b.city or "~").lower(), b.name.lower()),
    "size": lambda b: (b.child_count, b.name.lower()),
}


def branch_list(request):
    g = request.GET
    q = g.get("q", "").strip()
    level = g.get("level", "")
    area_slug, district_slug = g.get("area", ""), g.get("district", "")
    sort = g.get("sort", "type")
    descending = sort.startswith("-")
    key = sort.lstrip("-")
    if key not in SORTS:
        key, descending = "type", False

    everything, kids = _load_all()
    levels = dict(Branch.Level.choices)
    areas = sorted((b for b in everything if b.level == Branch.Level.AREA), key=lambda b: b.name.lower())
    districts = sorted((b for b in everything if b.level == Branch.Level.DISTRICT), key=lambda b: b.name.lower())
    totals = {val: sum(1 for b in everything if b.level == val) for val, _ in Branch.Level.choices}

    filtering = bool(q or level in levels or area_slug or district_slug or g.get("view") == "table" or "sort" in g)
    ctx = {
        "q": q, "level": level, "area": area_slug, "district": district_slug, "sort": key, "desc": descending,
        "level_chips": [(v, lbl, totals[v]) for v, lbl in Branch.Level.choices],
        "areas": areas, "districts": districts, "total": len(everything), "view": "table" if filtering else "tree",
    }
    if not filtering:
        ctx["tree"] = _tree(everything, kids)
        return render(request, "churches/list.html", ctx)

    rows = everything
    if level in levels:
        rows = [b for b in rows if b.level == level]
    if area_slug:
        rows = [b for b in rows if (b.area_unit and b.area_unit.slug == area_slug)]
    if district_slug:
        rows = [b for b in rows if (b.district_unit and b.district_unit.slug == district_slug)]
    if q:
        ql = q.lower()
        rows = [
            b for b in rows
            if ql in b.name.lower() or ql in b.city.lower() or ql in b.country.lower()
            or (b.superintendent and ql in b.superintendent.name.lower())
        ]
    rows = sorted(rows, key=SORTS[key], reverse=descending)
    page = Paginator(rows, PAGE_SIZE).get_page(g.get("page"))
    keep = {k: v for k, v in g.items() if k not in ("page", "sort") and v}
    def head(col, label):
        nxt = f"-{col}" if (key == col and not descending) else col
        state = ("descending" if descending else "ascending") if key == col else "none"
        return {"key": col, "label": label, "state": state, "href": "?" + urlencode(keep | {"sort": nxt})}

    ctx.update({
        "heads": [head("name", "Name"), head("type", "Type"), head("area", "Area"), head("district", "District"),
                  head("leader", "Led by"), head("city", "City"), head("size", "Units")],
        "page": page, "count": len(rows),
        "qs": urlencode(keep | ({"sort": ("-" if descending else "") + key} if "sort" in g else {})),
        "base_qs": urlencode(keep),
    })
    return render(request, "churches/list.html", ctx)


UNIT_PAGES = {
    "areas": (Branch.Level.AREA, "Areas", "Each area is led by an Area Superintendent and is made up of districts.",
              "Select an area to see its districts."),
    "districts": (Branch.Level.DISTRICT, "Districts", "Each district is led by a District Superintendent and gathers its stations.",
                  "Select a district to see its stations."),
    "stations": (Branch.Level.STATION, "Stations", "Stations are the local churches, where the church meets each week.",
                 "Select a station for its address, pastor and service times."),
}


def unit_list(request, kind):
    """Areas, districts and stations each get their own page, so an answer is one click away."""
    if kind not in UNIT_PAGES:
        raise Http404
    level, title, lede, hint = UNIT_PAGES[kind]
    g = request.GET
    q, area_slug, district_slug = g.get("q", "").strip(), g.get("area", ""), g.get("district", "")
    everything, kids = _load_all()
    areas = sorted((b for b in everything if b.level == Branch.Level.AREA), key=lambda b: b.name.lower())
    districts = sorted((b for b in everything if b.level == Branch.Level.DISTRICT), key=lambda b: b.name.lower())
    rows = [b for b in everything if b.level == level]
    for b in rows:
        direct = kids.get(b.pk, [])
        b.n_districts = len(direct) if b.level == Branch.Level.AREA else 0
        b.n_stations = (sum(len(kids.get(d.pk, [])) for d in direct) if b.level == Branch.Level.AREA
                        else len(direct) if b.level == Branch.Level.DISTRICT else 0)
    if area_slug:
        rows = [b for b in rows if (b.area_unit and b.area_unit.slug == area_slug) or b.slug == area_slug]
    if district_slug:
        rows = [b for b in rows if (b.district_unit and b.district_unit.slug == district_slug) or b.slug == district_slug]
    if q:
        ql = q.lower()
        rows = [b for b in rows if ql in b.name.lower() or ql in b.city.lower() or ql in b.address.lower()
                or (b.superintendent and ql in b.superintendent.name.lower())]
    if kind == "areas":
        rows.sort(key=lambda b: b.name.lower())
    else:  # the church's register order
        rows.sort(key=_order)
    page = Paginator(rows, 36).get_page(g.get("page"))
    keep = {k: v for k, v in g.items() if k != "page" and v}
    return render(request, "churches/units.html", {
        "kind": kind, "title": title, "lede": lede, "hint": hint, "level": level,
        "page": page, "count": len(rows), "q": q, "area": area_slug, "district": district_slug,
        "areas": areas, "districts": districts, "base_qs": urlencode(keep),
        "totals": {"areas": len(areas), "districts": len(districts),
                   "stations": sum(1 for b in everything if b.level == Branch.Level.STATION)},
        "hq": next((b for b in everything if b.is_national_headquarters), None),
    })


def headquarters(request):
    hq = Branch.objects.filter(is_national_headquarters=True, is_active=True).first()
    if not hq:
        messages.info(request, "The National Headquarters has not been set yet.")
        return redirect("churches:list")
    return redirect(hq)


def branch_detail(request, slug):
    branch = get_object_or_404(Branch.objects.select_related("parent"), slug=slug, is_active=True)
    user = request.user
    is_member = user.is_authenticated and Membership.objects.filter(user=user, branch=branch).exists()
    return render(
        request,
        "churches/detail.html",
        {
            "branch": branch,
            "active": "overview",
            "children": branch.children.filter(is_active=True).annotate(n_children=Count("children"))
            .prefetch_related(Prefetch("leaders", queryset=BranchLeader.objects.filter(is_current=True), to_attr="current_leaders"))
            .order_by("serial", "name"),
            "counts": branch.counts(),
            "leaders": [l for l in branch.leaders.filter(is_current=True)],
            "councils": _branch_councils(branch),
            "announcements": Announcement.objects.filter(branch=branch, is_published=True)[:5],
            "events": Event.objects.filter(branch=branch, starts_at__gte=timezone.now()).order_by("starts_at")[:3],
            "sermons": Sermon.objects.filter(branch=branch, is_published=True)[:3],
            "is_member": is_member,
            "can_manage": can_manage_branch(user, branch),
        },
    )


def _branch_councils(branch):
    from apps.leadership.models import Council
    return Council.objects.filter(branch=branch, is_active=True).prefetch_related("members")


@login_required
@require_POST
def join(request, slug):
    branch = get_object_or_404(Branch, slug=slug, is_active=True)
    _, created = join_branch(request.user, branch)
    messages.success(request, f"Welcome to {branch.name}!" if created else "You're already a member.")
    return redirect(branch)


@login_required
@require_POST
def leave(request, slug):
    branch = get_object_or_404(Branch, slug=slug)
    if leave_branch(request.user, branch):
        messages.success(request, f"You left {branch.name}.")
    return redirect(branch)
