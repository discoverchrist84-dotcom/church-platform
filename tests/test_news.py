import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.churches.models import Branch
from apps.news.models import NewsArticle

pytestmark = pytest.mark.django_db


def _n(title, **kw):
    kw.setdefault("body", "Story text.\n\nMore.")
    return NewsArticle.objects.create(title=title, **kw)


def test_news_page_shows_live_stories_only():
    _n("Convention opens")
    _n("Draft story", is_published=False)
    _n("Scheduled story", published_at=timezone.now() + timezone.timedelta(days=2))
    html = None
    from django.test import Client
    html = Client().get(reverse("news:list")).content.decode()
    assert "Convention opens" in html and "Draft story" not in html and "Scheduled story" not in html


def test_inside_and_outside_filters_and_search(client):
    _n("Our revival", scope="inside")
    _n("Floods in the region", scope="outside", topic="community", place="Abia")
    assert client.get(reverse("news:list"), {"scope": "outside"}).context["count"] == 1
    assert client.get(reverse("news:list"), {"scope": "inside"}).context["count"] == 1
    assert client.get(reverse("news:list"), {"q": "abia"}).context["count"] == 1
    assert client.get(reverse("news:list"), {"topic": "nonsense"}).status_code == 200


def test_filter_by_area_includes_its_districts_and_stations(client):
    area = Branch.objects.create(name="Aba Area", level="region")
    d = Branch.objects.create(name="Aba District", level="district", parent=area)
    s = Branch.objects.create(name="Ehi Road Station", level="local", parent=d)
    _n("At the station", branch=s)
    _n("Elsewhere")
    r = client.get(reverse("news:list"), {"unit": area.slug})
    assert [n.title for n in r.context["page"].object_list] == ["At the station"]


def test_detail_unsafe_source_link_is_not_rendered(client):
    n = _n("Report", scope="outside", source_name="Daily Paper", source_url="https://example.org/a")
    assert 'href="https://example.org/a"' in client.get(n.get_absolute_url()).content.decode()
    bad = NewsArticle(title="x", body="y", source_url="javascript:alert(1)")
    with pytest.raises(ValidationError):
        bad.full_clean()
    bad.save()
    assert bad.safe_source_url == ""


def test_draft_detail_is_404(client):
    n = _n("Hidden", is_published=False)
    assert client.get(n.get_absolute_url()).status_code == 404


def test_pinned_first_home_section_and_feed(client):
    _n("Old news", published_at=timezone.now() - timezone.timedelta(days=5))
    _n("Pinned news", is_pinned=True, published_at=timezone.now() - timezone.timedelta(days=9))
    titles = [n.title for n in client.get(reverse("news:list")).context["page"].object_list]
    assert titles[0] == "Pinned news"
    assert "Pinned news" in client.get(reverse("core:home")).content.decode()
    feed = client.get(reverse("news:feed"))
    assert feed.status_code == 200 and b"<rss" in feed.content


def test_admin_pages(admin_client):
    assert admin_client.get(reverse("admin:news_newsarticle_changelist")).status_code == 200
    assert admin_client.get(reverse("admin:news_newsarticle_add")).status_code == 200
