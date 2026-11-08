"""Search-engine basics: sitemap.xml, robots.txt, canonical/social tags and church markup."""
import json

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone

# Pages that belong to one person or to the admin: kept out of search results.
PRIVATE_PREFIXES = (
    "/admin/", "/accounts/", "/api/", "/notifications/", "/media/private",
    "/books/cart", "/books/checkout", "/books/orders", "/books/library", "/books/download", "/give/thanks",
)


class _Https(Sitemap):
    protocol = "http" if settings.DEBUG else "https"


class StaticPages(_Https):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ["core:home", "churches:list", "churches:areas", "churches:districts", "churches:stations",
                "leadership:list", "news:list", "news:bulletins", "bookstore:list", "history:timeline", "giving:give"]

    def location(self, name):
        return reverse(name)


class Branches(_Https):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        from apps.churches.models import Branch

        return Branch.objects.filter(is_active=True).order_by("level", "serial", "name")

    def lastmod(self, obj):
        return obj.updated_at


class NewsStories(_Https):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        from apps.news.models import NewsArticle

        return NewsArticle.objects.live()

    def lastmod(self, obj):
        return obj.updated_at


class Announcements(_Https):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        from apps.news.models import Bulletin

        return Bulletin.objects.filter(is_published=True, audience=Bulletin.Audience.ALL, published_at__lte=timezone.now())

    def lastmod(self, obj):
        return obj.updated_at


class Books(_Https):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        from apps.bookstore.models import Book

        return Book.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class History(_Https):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        from apps.history.models import Figure, HistoricalEvent

        return [*HistoricalEvent.objects.published(), *Figure.objects.published()]

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {"pages": StaticPages, "units": Branches, "news": NewsStories, "announcements": Announcements,
            "books": Books, "history": History}


def robots_txt(request):
    lines = ["User-agent: *"]
    lines += [f"Disallow: {p}" for p in PRIVATE_PREFIXES if not p.startswith("/media")]
    lines += ["Allow: /", "", f"Sitemap: {request.build_absolute_uri(reverse('sitemap'))}", ""]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def church_jsonld(request, info):
    """schema.org markup so search results can show the church's name, logo and contact details."""
    c = info.get("CONTACT") or {}
    data = {
        "@context": "https://schema.org",
        "@type": "Church",
        "name": info.get("SITE_NAME") or info.get("SITE_BRAND"),
        "url": request.build_absolute_uri("/"),
        "logo": request.build_absolute_uri(info.get("SITE_LOGO_URL", "")),
        "description": info.get("SITE_DESCRIPTION", ""),
    }
    if c.get("email"):
        data["email"] = c["email"]
    if c.get("phone"):
        data["telephone"] = c["phone"]
    if c.get("address"):
        data["address"] = {"@type": "PostalAddress", "streetAddress": c["address"]}
    if c.get("social"):
        data["sameAs"] = [u for _, u in c["social"]]
    # "<" is escaped so the text can never close the surrounding <script> tag.
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def seo_context(request, info):
    return {
        "CANONICAL_URL": request.build_absolute_uri(request.path),
        "OG_IMAGE_URL": request.build_absolute_uri(info.get("SITE_LOGO_URL", "")),
    }
