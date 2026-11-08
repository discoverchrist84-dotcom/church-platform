from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.pagination import paginate

from .models import Era, Figure, HistoricalEvent
from .services import search_events

router = Router()


class EraOut(Schema):
    id: int
    name: str
    slug: str
    start_year: int
    end_year: int | None = None
    summary: str


class EventListOut(Schema):
    id: int
    title: str
    slug: str
    when: str
    year_start: int
    summary: str
    era_slug: str | None = None

    @staticmethod
    def resolve_era_slug(obj):
        return obj.era.slug if obj.era_id else None


class SourceOut(Schema):
    id: int
    title: str
    author: str
    url: str
    kind: str


class FigureRef(Schema):
    name: str
    slug: str


class EventDetailOut(EventListOut):
    body: str
    figures: list[FigureRef]
    sources: list[SourceOut]
    tags: list[str]

    @staticmethod
    def resolve_figures(obj):
        return [f for f in obj.figures.all() if f.status == "published"]

    @staticmethod
    def resolve_sources(obj):
        return list(obj.sources.all())

    @staticmethod
    def resolve_tags(obj):
        return [t.name for t in obj.tags.all()]


class FigureOut(Schema):
    id: int
    name: str
    slug: str
    title: str
    lifespan: str
    bio: str


@router.get("/eras", response=list[EraOut])
def list_eras(request):
    return Era.objects.all()


@router.get("/events", response=list[EventListOut])
@paginate
def list_events(
    request,
    era: str | None = None,
    tag: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
):
    qs = HistoricalEvent.objects.published().select_related("era")
    if era:
        qs = qs.filter(era__slug=era)
    if tag:
        qs = qs.filter(tags__slug=tag)
    if year_from is not None:
        qs = qs.filter(year_start__gte=year_from)
    if year_to is not None:
        qs = qs.filter(year_start__lte=year_to)
    return qs


@router.get("/events/{slug}", response=EventDetailOut)
def get_event(request, slug: str):
    qs = (
        HistoricalEvent.objects.published()
        .select_related("era")
        .prefetch_related("figures", "sources", "tags")
    )
    return get_object_or_404(qs, slug=slug)


@router.get("/figures", response=list[FigureOut])
@paginate
def list_figures(request, q: str | None = None):
    qs = Figure.objects.published()
    if q:
        qs = qs.filter(name__icontains=q)
    return qs


@router.get("/figures/{slug}", response=FigureOut)
def get_figure(request, slug: str):
    return get_object_or_404(Figure.objects.published(), slug=slug)


@router.get("/search", response=list[EventListOut])
def search(request, q: str):
    return list(search_events(q)[:25])
