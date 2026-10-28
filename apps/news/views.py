from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.contrib.syndication.views import Feed

from apps.churches.models import Branch

from .models import NewsArticle

PAGE_SIZE = 9


def _unit_ids(slug):
    unit = Branch.objects.filter(slug=slug, is_active=True).first()
    return unit, ([unit.pk] + [b.pk for b in unit.descendants()]) if unit else []


def news_list(request):
    g = request.GET
    q, scope, topic, unit_slug = g.get("q", "").strip(), g.get("scope", ""), g.get("topic", ""), g.get("unit", "")
    qs = NewsArticle.objects.live().select_related("branch")
    if scope in dict(NewsArticle.Scope.choices):
        qs = qs.filter(scope=scope)
    if topic in dict(NewsArticle.Topic.choices):
        qs = qs.filter(topic=topic)
    unit = None
    if unit_slug:
        unit, ids = _unit_ids(unit_slug)
        qs = qs.filter(branch_id__in=ids)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q) | Q(place__icontains=q))
    page = Paginator(qs, PAGE_SIZE).get_page(g.get("page"))
    keep = "&".join(f"{k}={v}" for k, v in g.items() if k != "page" and v)
    return render(request, "news/list.html", {
        "page": page, "q": q, "scope": scope, "topic": topic, "unit": unit, "unit_slug": unit_slug,
        "scopes": NewsArticle.Scope.choices, "topics": NewsArticle.Topic.choices, "base_qs": keep,
        "units": Branch.objects.filter(is_active=True, level__in=["region", "district"]).order_by("level", "name"),
        "count": page.paginator.count,
    })


def news_detail(request, slug):
    item = get_object_or_404(NewsArticle.objects.live().select_related("branch"), slug=slug)
    related = (NewsArticle.objects.live().filter(Q(topic=item.topic) | Q(scope=item.scope)).exclude(pk=item.pk)[:3])
    return render(request, "news/detail.html", {
        "item": item, "related": related,
        "paragraphs": [p.strip() for p in item.body.split("\n\n") if p.strip()],
    })


class NewsFeed(Feed):
    """RSS feed so people can follow the news in a feed reader."""
    title = "Church news"
    link = "/news/"
    description = "News and updates from inside and outside the church."

    def items(self):
        return NewsArticle.objects.live().order_by("-published_at")[:30]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt

    def item_pubdate(self, item):
        return item.published_at
