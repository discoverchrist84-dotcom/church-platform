from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from .models import Era, Figure, HistoricalEvent
from .services import search_events


def timeline(request):
    """Eras in order, each with its published events."""
    events = HistoricalEvent.objects.published()
    eras = Era.objects.prefetch_related(Prefetch("events", queryset=events))
    unassigned = events.filter(era__isnull=True)
    return render(request, "history/timeline.html", {"eras": eras, "unassigned": unassigned})


def event_detail(request, slug):
    qs = (
        HistoricalEvent.objects.published()
        .select_related("era")
        .prefetch_related("figures", "places", "sources", "tags")
    )
    event = get_object_or_404(qs, slug=slug)
    paragraphs = [p.strip() for p in event.body.split("\n\n") if p.strip()]
    return render(
        request,
        "history/event_detail.html",
        {
            "event": event,
            "paragraphs": paragraphs,
            "figures": [f for f in event.figures.all() if f.status == "published"],
        },
    )


def figure_detail(request, slug):
    figure = get_object_or_404(Figure.objects.published(), slug=slug)
    paragraphs = [p.strip() for p in figure.bio.split("\n\n") if p.strip()]
    events = figure.events.filter(status="published")
    return render(
        request,
        "history/figure_detail.html",
        {"figure": figure, "paragraphs": paragraphs, "events": events},
    )


def search_page(request):
    q = request.GET.get("q", "").strip()
    results = search_events(q)[:50] if q else []
    return render(request, "history/search.html", {"q": q, "results": results})
