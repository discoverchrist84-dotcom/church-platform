from django.conf import settings
from django.db.models import Q

from .models import HistoricalEvent


def search_events(query: str):
    """Search published events.

    Uses Postgres full-text search with ranking when running on Postgres;
    falls back to case-insensitive matching elsewhere (e.g. SQLite in dev).
    """
    query = (query or "").strip()
    qs = HistoricalEvent.objects.published().select_related("era")
    if not query:
        return qs.none()

    if settings.USING_POSTGRES:
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        vector = SearchVector("title", weight="A") + SearchVector("summary", weight="B") + SearchVector("body", weight="C")
        sq = SearchQuery(query, search_type="websearch")
        return (
            qs.annotate(rank=SearchRank(vector, sq), search=vector)
            .filter(search=sq)
            .order_by("-rank", "year_start")
        )

    return qs.filter(Q(title__icontains=query) | Q(summary__icontains=query) | Q(body__icontains=query))
