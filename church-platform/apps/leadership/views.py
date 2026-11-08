from django.shortcuts import get_object_or_404, render

from .models import Council, CouncilMember


def council_list(request):
    qs = Council.objects.filter(is_active=True).select_related("branch").prefetch_related("members")
    general = [c for c in qs if c.is_general]
    others = [c for c in qs if not c.is_general]
    return render(request, "leadership/list.html", {"general": general, "others": others})


def council_detail(request, slug):
    council = get_object_or_404(Council.objects.select_related("branch"), slug=slug, is_active=True)
    members = list(council.members.all())
    return render(request, "leadership/council.html", {
        "council": council,
        "current": [m for m in members if m.is_current],
        "past": [m for m in members if not m.is_current],
    })


def member_detail(request, slug, pk):
    council = get_object_or_404(Council, slug=slug, is_active=True)
    member = get_object_or_404(CouncilMember, pk=pk, council=council)
    return render(request, "leadership/member.html", {"council": council, "member": member})
