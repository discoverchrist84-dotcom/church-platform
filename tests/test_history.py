import pytest
from django.urls import reverse

from apps.core.models import PublishStatus
from apps.history.models import Era, HistoricalEvent, format_year
from apps.history.services import search_events

pytestmark = pytest.mark.django_db


@pytest.fixture
def era():
    return Era.objects.create(name="Early Church", slug="early-church", start_year=100)


@pytest.fixture
def events(era):
    pub = HistoricalEvent.objects.create(
        title="Council of Nicaea", slug="nicaea", era=era, year_start=325,
        summary="First ecumenical council.", status=PublishStatus.PUBLISHED,
    )
    draft = HistoricalEvent.objects.create(
        title="Secret Draft", slug="draft", era=era, year_start=400,
        summary="Not ready.", status=PublishStatus.DRAFT,
    )
    return pub, draft


def test_format_year():
    assert format_year(-4) == "4 BC"
    assert format_year(325) == "AD 325"
    assert format_year(None) == ""


def test_publishing_sets_published_at(events):
    pub, draft = events
    assert pub.published_at is not None
    assert draft.published_at is None


def test_api_lists_only_published(client, events):
    resp = client.get("/api/history/events")
    assert resp.status_code == 200
    slugs = [e["slug"] for e in resp.json()["items"]]
    assert slugs == ["nicaea"]


def test_draft_event_is_404(client, events):
    assert client.get("/api/history/events/draft").status_code == 404
    assert client.get(reverse("history:event", args=["draft"])).status_code == 404


def test_search_finds_published_only(events):
    assert [e.slug for e in search_events("Nicaea")] == ["nicaea"]
    assert list(search_events("Secret")) == []
    assert list(search_events("")) == []


def test_pages_render(client, events):
    assert client.get(reverse("history:timeline")).status_code == 200
    assert client.get(reverse("history:event", args=["nicaea"])).status_code == 200
    assert client.get(reverse("history:search") + "?q=nicaea").status_code == 200
