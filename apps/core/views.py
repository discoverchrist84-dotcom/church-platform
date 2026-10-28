from pathlib import Path

from django.conf import settings
from django.db.models import Count
from django.http import FileResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.cache import never_cache

from apps.churches.models import Branch
from apps.core.site_info import site_info
from apps.community.models import Event
from apps.history.models import Era, HistoricalEvent


def _home_stats():
    """Headline numbers for the landing page (cheap grouped counts)."""
    from django.contrib.auth import get_user_model

    levels = dict(Branch.objects.filter(is_active=True).values_list("level").annotate(n=Count("id")))
    return {
        "areas": levels.get(Branch.Level.AREA, 0),
        "districts": levels.get(Branch.Level.DISTRICT, 0),
        "stations": levels.get(Branch.Level.STATION, 0),
        "members": get_user_model().objects.filter(is_active=True).count(),
    }


def _spotlight():
    from apps.leadership.models import Council

    council = (
        Council.objects.filter(is_active=True, branch__isnull=True)
        .prefetch_related("members")
        .first()
    )
    if not council:
        return None, []
    return council, [m for m in council.members.all() if m.is_current][:6]


def _home_news():
    from apps.news.models import NewsArticle

    return list(NewsArticle.objects.live().select_related("branch")[:3])


def _home_books():
    from apps.bookstore.models import Book

    return list(Book.objects.filter(is_published=True).order_by("-is_featured", "-created_at").prefetch_related("authors")[:4])


def _home_devotional():
    from apps.bookstore.models import DevotionalEntry

    today = timezone.localdate()
    qs = DevotionalEntry.objects.filter(is_published=True, date__lte=today)
    return qs.filter(date=today).first() or qs.first()


def home(request):
    council, council_members = _spotlight()
    return render(
        request,
        "core/home.html",
        {
            "stats": _home_stats(),
            "spot_council": council,
            "spot_members": council_members,
            "hq": Branch.objects.filter(is_national_headquarters=True, is_active=True).first(),
            "home_news": _home_news(),
            "home_books": _home_books(),
            "devotional": _home_devotional(),
            "eras": Era.objects.all()[:6],
            "featured_events": HistoricalEvent.objects.published().select_related("era")[:6],
            "branches": Branch.objects.filter(is_active=True)[:6],
            "upcoming": Event.objects.filter(starts_at__gte=timezone.now())
            .select_related("branch")
            .order_by("starts_at")[:3],
        },
    )


def offline(request):
    return render(request, "core/offline.html")


def manifest(request):
    """Web app manifest: makes the site installable (Android/desktop Chrome, Edge, Safari)."""
    info = site_info()
    data = {
        "name": info["SITE_NAME"],
        "short_name": info["SITE_SHORT_NAME"],
        "description": info["SITE_DESCRIPTION"],
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "theme_color": settings.THEME_COLOR,
        "background_color": settings.BACKGROUND_COLOR,
        "icons": [
            {"src": static("icons/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("icons/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {
                "src": static("icons/maskable-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")


@never_cache
def service_worker(request):
    """Serve the SW from the site root so its scope covers the whole site."""
    path = Path(settings.BASE_DIR) / "static" / "js" / "service-worker.js"
    response = FileResponse(open(path, "rb"), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response
